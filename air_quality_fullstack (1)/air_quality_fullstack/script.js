const API_URL = "http://127.0.0.1:8000";
const fileInput=document.getElementById("dataset"), analyzeBtn=document.getElementById("analyze-btn");
const statusEl=document.getElementById("status"), fileName=document.getElementById("file-name");
let resultData=null, predictionChart=null, importanceChart=null;
fileInput.addEventListener("change",()=>{const f=fileInput.files[0];fileName.textContent=f?f.name:"No file selected";analyzeBtn.disabled=!f;});
const drop=document.querySelector(".dropzone");
drop.addEventListener("dragover",e=>{e.preventDefault();drop.classList.add("dragging");});
drop.addEventListener("dragleave",()=>drop.classList.remove("dragging"));
drop.addEventListener("drop",e=>{e.preventDefault();drop.classList.remove("dragging");if(e.dataTransfer.files.length){fileInput.files=e.dataTransfer.files;fileInput.dispatchEvent(new Event("change"));}});
analyzeBtn.addEventListener("click",async()=>{
 const file=fileInput.files[0];if(!file)return;
 const form=new FormData();form.append("file",file);
 analyzeBtn.disabled=true;statusEl.className="status";statusEl.textContent="Processing data and training the models…";
 try{
  const response=await fetch(`${API_URL}/analyze`,{method:"POST",body:form});
  const data=await response.json();if(!response.ok)throw new Error(data.detail||"Analysis failed");
  resultData=data;renderResults(data);statusEl.textContent="Analysis completed successfully.";document.getElementById("results").classList.remove("hidden");
 }catch(err){statusEl.className="status error";statusEl.textContent=`${err.message}. Check that the Python API server is running.`;}
 finally{analyzeBtn.disabled=false;}
});
function renderResults(d){
 document.getElementById("usable").textContent=d.usable_records.toLocaleString();
 document.getElementById("test-count").textContent=d.test_records.toLocaleString();
 document.getElementById("flag-count").textContent=d.residual_flag_count.toLocaleString();
 document.getElementById("both-count").textContent=d.both_flag_count.toLocaleString();
 document.getElementById("metrics-body").innerHTML=d.metrics.map(m=>`<tr><td>${m.Model}</td><td>${m.MAE.toFixed(3)}</td><td>${m.RMSE.toFixed(3)}</td><td>${m.R2.toFixed(3)}</td></tr>`).join("");
 const p=d.predictions;
 if(predictionChart)predictionChart.destroy();
 predictionChart=new Chart(document.getElementById("prediction-chart"),{type:"line",data:{labels:p.map(x=>new Date(x.datetime).toLocaleDateString()),datasets:[{label:"Actual CO",data:p.map(x=>x.real),borderColor:"#176b57",pointRadius:0,borderWidth:2},{label:"Predicted CO",data:p.map(x=>x.predicted),borderColor:"#d18b45",pointRadius:0,borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:"bottom"}},scales:{x:{ticks:{maxTicksLimit:7}}}}});
 if(importanceChart)importanceChart.destroy();
 const imp=d.feature_importance;
 importanceChart=new Chart(document.getElementById("importance-chart"),{type:"bar",data:{labels:imp.map(x=>x.feature),datasets:[{label:"Importance",data:imp.map(x=>x.importance),backgroundColor:"#5a9b82",borderRadius:4}]},options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}});
 const flags=d.flagged_hours;
 document.getElementById("flags-body").innerHTML=flags.length?flags.map(x=>`<tr><td>${new Date(x.datetime).toLocaleString()}</td><td>${Number(x.real).toFixed(3)}</td><td>${Number(x.predicted).toFixed(3)}</td><td>${Number(x.error).toFixed(3)}</td><td>${x.flag_both?"Both":x.flag_isolation?"Isolation Forest":"Residual"}</td><td>${x.explanation}</td></tr>`).join(""):'<tr><td colspan="6">No residual-flagged hours in this test period.</td></tr>';
}
document.getElementById("download-btn").addEventListener("click",()=>{if(!resultData)return;const rows=resultData.flagged_hours;const cols=["datetime","real","predicted","error","flag_residual","flag_isolation","flag_both","hour","month","missing_nearby","explanation"];const csv=[cols.join(","),...rows.map(r=>cols.map(c=>JSON.stringify(r[c]??"")).join(","))].join("\n");const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([csv],{type:"text/csv"}));a.download="flagged_hours.csv";a.click();URL.revokeObjectURL(a.href);});
