from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from io import BytesIO
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

app=FastAPI(title="AirSight Air Quality API")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/")
def root():
    return {"message":"AirSight API is running. POST an Excel dataset to /analyze."}

@app.post("/analyze")
async def analyze(file: UploadFile=File(...)):
    if not file.filename.lower().endswith((".xlsx",".xls")):
        raise HTTPException(400,"Please upload an .xlsx or .xls Excel file.")
    try:
        df=pd.read_excel(BytesIO(await file.read()))
        required={"Date","Time","CO(GT)","PT08.S1(CO)","PT08.S2(NMHC)","PT08.S3(NOx)","PT08.S4(NO2)","PT08.S5(O3)","T","RH","AH"}
        missing=required-set(df.columns)
        if missing: raise ValueError("Missing columns: "+", ".join(sorted(missing)))
        df=df.replace(-200,np.nan)
        df["datetime"]=pd.to_datetime(df["Date"].astype(str)+" "+df["Time"].astype(str),errors="coerce")
        df=df.dropna(subset=["datetime"]).sort_values("datetime").set_index("datetime")
        df=df.drop(columns=["Date","Time","NMHC(GT)"],errors="ignore")
        target="CO(GT)"
        sensors=["PT08.S1(CO)","PT08.S2(NMHC)","PT08.S3(NOx)","PT08.S4(NO2)","PT08.S5(O3)"]
        weather=["T","RH","AH"]
        data=df[[target]+sensors+weather].copy()
        data=data[~data.index.duplicated(keep="first")].asfreq("h").interpolate(limit=3)
        for lag in [1,2,3,24]: data[f"CO_lag{lag}"]=data[target].shift(lag)
        data["CO_roll6"]=data[target].shift(1).rolling(6).mean()
        data["hour"]=data.index.hour
        data["dayofweek"]=data.index.dayofweek
        data=data.dropna()
        if len(data)<30: raise ValueError("Not enough usable hourly rows after cleaning. Upload a larger dataset.")
        feature_cols=[c for c in data.columns if c!=target]
        X,y=data[feature_cols],data[target]
        split=int(len(data)*.8)
        X_train,X_test=X.iloc[:split],X.iloc[split:]
        y_train,y_test=y.iloc[:split],y.iloc[split:]
        if len(X_test)<2: raise ValueError("Not enough test records.")
        def scores(name,actual,pred):
            return {"Model":name,"MAE":float(mean_absolute_error(actual,pred)),
                    "RMSE":float(np.sqrt(mean_squared_error(actual,pred))),"R2":float(r2_score(actual,pred))}
        naive=X_test["CO_lag1"]
        scaler=StandardScaler().fit(X_train)
        ridge=Ridge(alpha=1.0).fit(scaler.transform(X_train),y_train)
        ridge_pred=ridge.predict(scaler.transform(X_test))
        rf=RandomForestRegressor(n_estimators=300,min_samples_leaf=3,random_state=42,n_jobs=-1)
        rf.fit(X_train,y_train)
        rf_pred=pd.Series(rf.predict(X_test),index=y_test.index)
        metrics=[scores("Naive (last hour)",y_test,naive),scores("Ridge",y_test,ridge_pred),scores("Random Forest",y_test,rf_pred)]
        residual=y_test-rf_pred
        flag_resid=residual.abs()>(2.5*residual.std())
        iso_data=X_test.copy();iso_data[target]=y_test
        iso=IsolationForest(n_estimators=200,contamination=.05,random_state=42)
        flag_iso=pd.Series(iso.fit_predict(iso_data)==-1,index=iso_data.index)
        flag_both=flag_resid&flag_iso
        # Check whether CO ground-truth readings were missing in the previous 1-3 hours.
        orig_missing=df[target].isna()
        records=[]
        for t in y_test.index[flag_resid]:
            err=float(residual.loc[t])
            nearby=any(bool(orig_missing.get(t-pd.Timedelta(hours=h),True)) for h in (1,2,3))
            if nearby: explanation="Possible data limitation (missing data nearby)"
            elif err>0: explanation="Real spike? (CO higher than expected)"
            else: explanation="Real drop? (CO lower than expected)"
            records.append({"datetime":t.isoformat(),"real":float(y_test.loc[t]),"predicted":float(rf_pred.loc[t]),
              "error":err,"flag_residual":bool(flag_resid.loc[t]),"flag_isolation":bool(flag_iso.loc[t]),
              "flag_both":bool(flag_both.loc[t]),"hour":int(t.hour),"month":int(t.month),
              "missing_nearby":nearby,"explanation":explanation})
        preds=[{"datetime":t.isoformat(),"real":float(y_test.loc[t]),"predicted":float(rf_pred.loc[t])} for t in y_test.index]
        importance=[{"feature":str(k),"importance":float(v)} for k,v in pd.Series(rf.feature_importances_,index=feature_cols).sort_values().items()]
        return {"usable_records":int(len(data)),"test_records":int(len(y_test)),"residual_flag_count":int(flag_resid.sum()),
          "isolation_flag_count":int(flag_iso.sum()),"both_flag_count":int(flag_both.sum()),"metrics":metrics,
          "predictions":preds,"feature_importance":importance,"flagged_hours":records}
    except Exception as e:
        raise HTTPException(400,str(e))
