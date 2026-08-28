import React, { useState, useEffect, useRef } from "react";
import { 
  UploadCloud, FileText, Settings, Play, Sparkles, Clock, 
  BookOpen, Layers, RefreshCw, Download, CheckCircle2, 
  AlertTriangle, ChevronRight, Edit3, Volume2, ArrowLeft, 
  XCircle, Film, Info, HelpCircle
} from "lucide-react";

// API Base URL - points to the FastAPI backend
const API_BASE = "http://localhost:8000";

interface Scene {
  id: number;
  title: string;
  duration: number;
  narration: string;
  visual_prompt: str;
  on_screen_text: string[];
  animation: string;
  transition: string;
  actual_duration?: number;
}

interface Script {
  title: string;
  summary: string;
  target_duration: number;
  scenes: Scene[];
}

interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  current_stage: string;
  current_scene: number;
  total_scenes: number;
  video_url: string | null;
  error_message: string | null;
  logs?: string[];
  script?: Script | null;
}

export default function App() {
  // Navigation State
  const [page, setPage] = useState<"landing" | "create" | "generation" | "result">("landing");
  
  // Create Form State
  const [topic, setTopic] = useState("");
  const [textInput, setTextInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");
  const [extractedText, setExtractedText] = useState("");
  
  // Settings State
  const [duration, setDuration] = useState(180); // in seconds
  const [customDuration, setCustomDuration] = useState("3");
  const [difficulty, setDifficulty] = useState("Intermediate");
  const [style, setStyle] = useState("Professor");
  
  // Active Job State
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [script, setScript] = useState<Script | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [pollingActive, setPollingActive] = useState(false);
  
  // Scene Editor State
  const [editingScene, setEditingScene] = useState<Scene | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editNarration, setEditNarration] = useState("");
  const [editPrompt, setEditPrompt] = useState("");
  const [editText, setEditText] = useState("");
  const [isUpdatingScene, setIsUpdatingScene] = useState(false);

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (uploadedFile: File) => {
    const ext = uploadedFile.name.split('.').pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "txt") {
      alert("Unsupported file format. Please upload a PDF or TXT file.");
      return;
    }
    
    setFile(uploadedFile);
    setUploadStatus("uploading");
    
    const formData = new FormData();
    formData.append("file", uploadedFile);
    
    try {
      const res = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
        body: formData
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Upload failed");
      }
      const data = await res.json();
      setExtractedText(data.extracted_text);
      setUploadStatus("success");
    } catch (e: any) {
      console.error(e);
      setUploadStatus("error");
      alert(`Text extraction failed: ${e.message}`);
    }
  };

  // Try Example Preset loader
  const loadExample = () => {
    setTopic("Explain the OSI Model");
    setTextInput(
      "The Open Systems Interconnection model is a conceptual model that characterises and standardises the communication functions of a telecommunication or computing system without regard to its underlying internal structure and technology. It divides communication into seven logical layers: Physical, Data Link, Network, Transport, Session, Presentation, and Application."
    );
    setDuration(120);
    setDifficulty("Intermediate");
    setStyle("Notebook");
    setPage("create");
  };

  // Triggers Pipeline
  const handleGenerateVideo = async () => {
    setErrorMsg(null);
    setJobId(null);
    setJobStatus(null);
    
    // Resolve final text to analyze
    const textToProcess = extractedText || textInput || topic;
    if (!textToProcess.trim()) {
      alert("Please upload a document, enter a topic, or paste some text content.");
      return;
    }

    setPage("generation");
    
    try {
      // 1. Script Generation
      const scriptRes = await fetch(`${API_BASE}/api/generate-script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textToProcess,
          duration: duration,
          difficulty: difficulty,
          style: style,
          topic: topic
        })
      });
      
      if (!scriptRes.ok) {
        const errorData = await scriptRes.json();
        throw new Error(errorData.detail || "Script generation failed");
      }
      
      const scriptData = await scriptRes.json();
      const generatedScript = scriptData.script;
      setScript(generatedScript);

      // 2. Submit Render Job
      const renderRes = await fetch(`${API_BASE}/api/video/generate-video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textToProcess,
          script: generatedScript,
          difficulty: difficulty,
          style: style,
          topic: topic || generatedScript.title
        })
      });

      if (!renderRes.ok) {
        const errorData = await renderRes.json();
        throw new Error(errorData.detail || "Video submission failed");
      }

      const renderData = await renderRes.json();
      setJobId(renderData.job_id);
      setPollingActive(true);
    } catch (e: any) {
      console.error(e);
      setErrorMsg(e.message || "An unexpected error occurred during generation.");
    }
  };

  // Polling logic for video job status
  useEffect(() => {
    let timer: any;
    if (pollingActive && jobId) {
      const fetchStatus = async () => {
        try {
          const res = await fetch(`${API_BASE}/api/video/${jobId}`);
          if (!res.ok) throw new Error("Failed to poll status");
          const data: JobStatus = await res.json();
          
          setJobStatus(data);
          if (data.script) {
            setScript(data.script);
          }

          if (data.status === "completed") {
            setPollingActive(false);
            setPage("result");
          } else if (data.status === "failed") {
            setPollingActive(false);
            setErrorMsg(data.error_message || "Video rendering pipeline failed.");
          }
        } catch (err: any) {
          console.error("Polling error:", err);
        }
      };

      // Poll every 2.5 seconds
      fetchStatus();
      timer = setInterval(fetchStatus, 2500);
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [pollingActive, jobId]);

  // Cancel generation
  const handleCancelGeneration = () => {
    setPollingActive(false);
    setJobId(null);
    setJobStatus(null);
    setPage("create");
  };

  // Open Scene Editor
  const openEditor = (scene: Scene) => {
    setEditingScene(scene);
    setEditTitle(scene.title);
    setEditNarration(scene.narration);
    setEditPrompt(scene.visual_prompt);
    setEditText(scene.on_screen_text.join(", "));
  };

  // Save/Update Scene
  const handleRegenerateScene = async () => {
    if (!editingScene || !jobId) return;
    setIsUpdatingScene(true);

    try {
      const res = await fetch(`${API_BASE}/api/video/scene/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_id: jobId,
          scene_id: editingScene.id,
          title: editTitle,
          narration: editNarration,
          visual_prompt: editPrompt,
          on_screen_text: editText.split(",").map(t => t.trim()).filter(Boolean)
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to update scene");
      }

      const data = await res.json();
      
      // Update local script list
      if (data.job && data.job.script) {
        setScript(data.job.script);
      }
      
      setEditingScene(null);
      alert("Scene updated successfully! The video is rebuilding with the updated clip.");
      
      // Reload page state or video source
      setPage("result");
    } catch (e: any) {
      alert(`Failed to update scene: ${e.message}`);
    } finally {
      setIsUpdatingScene(false);
    }
  };

  // Helper: Format duration into readable seconds
  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs < 10 ? '0' : ''}${remainingSecs}`;
  };

  return (
    <div className="min-h-screen grid-bg text-foreground flex flex-col justify-between">
      {/* HEADER */}
      <header className="border-b border-border/60 bg-background/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setPage("landing")}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-purple-600 flex items-center justify-center glow-primary">
              <Film className="w-5 h-5 text-background" />
            </div>
            <div>
              <h1 className="font-bold text-xl tracking-tight text-glow">StudyFlow <span className="text-primary">AI</span></h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-semibold">Video Overview Studio</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <span className="text-xs py-1 px-2.5 rounded-full bg-primary/10 border border-primary/20 text-primary font-medium flex items-center gap-1.5 animate-pulse-slow">
              <Sparkles className="w-3.5 h-3.5" /> Low-Resource Active
            </span>
          </div>
        </div>
      </header>

      {/* PAGE CONTAINERS */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-6 py-12 flex flex-col justify-center">
        
        {/* LANDING PAGE */}
        {page === "landing" && (
          <div className="text-center py-12 max-w-4xl mx-auto flex flex-col items-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-muted-foreground text-xs mb-6 hover:border-white/20 transition-all cursor-pointer">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              <span>Free, open-source Microsoft Edge narration and custom diagrams</span>
            </div>
            
            <h2 className="text-5xl md:text-6xl font-extrabold tracking-tight mb-6 leading-tight">
              Turn your notes into <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary via-blue-400 to-purple-500">
                educational videos
              </span>.
            </h2>
            
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 leading-relaxed">
              Upload a document or enter a topic. StudyFlow AI maps content into storyboarded scenes, generates voiceovers, compiles slides, and produces a complete explainer video automatically.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <button 
                onClick={() => setPage("create")}
                className="px-8 py-4 rounded-xl bg-primary text-background font-bold text-base hover:bg-opacity-90 transition-all flex items-center gap-2 group shadow-lg glow-primary"
              >
                Create Video <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              
              <button 
                onClick={loadExample}
                className="px-8 py-4 rounded-xl bg-white/5 border border-white/10 text-foreground font-semibold text-base hover:bg-white/10 hover:border-white/20 transition-all"
              >
                Try Example
              </button>
            </div>

            {/* Feature Badges */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20 w-full">
              <div className="glass-panel p-6 rounded-2xl flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                  <FileText className="w-5 h-5 text-primary" />
                </div>
                <h4 className="font-semibold text-sm mb-1">Doc Extraction</h4>
                <p className="text-xs text-muted-foreground">Extract clean text from large PDFs</p>
              </div>
              <div className="glass-panel p-6 rounded-2xl flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                  <BookOpen className="w-5 h-5 text-primary" />
                </div>
                <h4 className="font-semibold text-sm mb-1">Pedagogical Scripts</h4>
                <p className="text-xs text-muted-foreground">Structured JSON storyboard models</p>
              </div>
              <div className="glass-panel p-6 rounded-2xl flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                  <Volume2 className="w-5 h-5 text-primary" />
                </div>
                <h4 className="font-semibold text-sm mb-1">Edge Narration</h4>
                <p className="text-xs text-muted-foreground">Natural, zero-cost AI speech voices</p>
              </div>
              <div className="glass-panel p-6 rounded-2xl flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
                  <Layers className="w-5 h-5 text-primary" />
                </div>
                <h4 className="font-semibold text-sm mb-1">Scene Editor</h4>
                <p className="text-xs text-muted-foreground">Regenerate single scenes instantly</p>
              </div>
            </div>
          </div>
        )}

        {/* CREATE VIDEO PAGE */}
        {page === "create" && (
          <div className="max-w-4xl mx-auto w-full">
            <button 
              onClick={() => setPage("landing")}
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground text-sm mb-8 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Landing
            </button>
            
            <h2 className="text-3xl font-bold tracking-tight mb-8">Generate Educational Video</h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Input Workspace */}
              <div className="lg:col-span-2 space-y-6">
                <div className="glass-panel p-6 rounded-2xl">
                  <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" /> Content Input
                  </h3>
                  
                  {/* PDF Upload Area */}
                  <div 
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
                      isDragging 
                        ? "border-primary bg-primary/5" 
                        : uploadStatus === "success" 
                          ? "border-green-500/50 bg-green-500/5" 
                          : "border-border hover:border-white/20"
                    }`}
                  >
                    <input 
                      type="file" 
                      id="doc-upload" 
                      className="hidden" 
                      accept=".pdf,.txt"
                      onChange={handleFileChange}
                    />
                    
                    <label htmlFor="doc-upload" className="cursor-pointer flex flex-col items-center">
                      <UploadCloud className={`w-12 h-12 mb-4 ${
                        uploadStatus === "success" ? "text-green-500" : "text-muted-foreground"
                      }`} />
                      
                      {uploadStatus === "uploading" ? (
                        <p className="font-medium text-sm text-primary animate-pulse">Extracting text from document...</p>
                      ) : uploadStatus === "success" && file ? (
                        <div>
                          <p className="font-medium text-sm text-green-500 flex items-center gap-1 justify-center">
                            <CheckCircle2 className="w-4 h-4" /> Loaded: {file.name}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">({extractedText.length} characters parsed)</p>
                        </div>
                      ) : (
                        <div>
                          <p className="font-semibold text-sm">Drag & drop your PDF / TXT here</p>
                          <p className="text-xs text-muted-foreground mt-1">or click to browse from files (max 15MB)</p>
                        </div>
                      )}
                    </label>
                  </div>

                  <div className="relative my-6 text-center">
                    <div className="absolute inset-0 flex items-center" aria-hidden="true">
                      <div className="w-full border-t border-border/60"></div>
                    </div>
                    <span className="relative px-3 bg-[#0f0f12] text-xs text-muted-foreground uppercase font-semibold">OR</span>
                  </div>

                  {/* Topic / Plain Text Input */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Topic Heading</label>
                      <input 
                        type="text"
                        placeholder="e.g. CPU Scheduling Algorithms"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        className="w-full bg-input border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Source Text Notes</label>
                      <textarea 
                        rows={5}
                        placeholder="Paste your source text details or study guides here..."
                        value={textInput}
                        onChange={(e) => setTextInput(e.target.value)}
                        className="w-full bg-input border border-border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Side Config Panel */}
              <div className="space-y-6">
                <div className="glass-panel p-6 rounded-2xl">
                  <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-primary" /> Settings
                  </h3>

                  <div className="space-y-6">
                    {/* Duration Select */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2.5">Target Duration</label>
                      <div className="grid grid-cols-2 gap-2 mb-2">
                        {[
                          { label: "2 Min", val: 120 },
                          { label: "3 Min", val: 180 },
                          { label: "5 Min", val: 300 },
                          { label: "Custom", val: -1 }
                        ].map((d) => (
                          <button
                            key={d.label}
                            type="button"
                            onClick={() => setDuration(d.val)}
                            className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all ${
                              (d.val === duration || (d.val === -1 && ![120, 180, 300].includes(duration)))
                                ? "bg-primary text-background border-primary shadow-sm"
                                : "bg-white/5 border-border hover:bg-white/10"
                            }`}
                          >
                            {d.label}
                          </button>
                        ))}
                      </div>
                      {![120, 180, 300].includes(duration) && (
                        <div className="flex items-center gap-2 mt-2">
                          <input 
                            type="number"
                            value={customDuration}
                            onChange={(e) => {
                              setCustomDuration(e.target.value);
                              const parsed = parseInt(e.target.value);
                              if (parsed > 0) setDuration(parsed * 60);
                            }}
                            className="w-20 bg-input border border-border rounded-lg px-2.5 py-1.5 text-xs focus:outline-none"
                          />
                          <span className="text-xs text-muted-foreground">Minutes</span>
                        </div>
                      )}
                    </div>

                    {/* Difficulty */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2.5">Difficulty Level</label>
                      <div className="flex gap-2">
                        {["Beginner", "Intermediate", "Advanced"].map((lvl) => (
                          <button
                            key={lvl}
                            type="button"
                            onClick={() => setDifficulty(lvl)}
                            className={`flex-1 py-2 px-1 rounded-lg text-xs font-semibold border transition-all ${
                              difficulty === lvl 
                                ? "bg-primary text-background border-primary shadow-sm" 
                                : "bg-white/5 border-border hover:bg-white/10"
                            }`}
                          >
                            {lvl}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Teaching Style */}
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2.5">Teaching Style</label>
                      <select 
                        value={style}
                        onChange={(e) => setStyle(e.target.value)}
                        className="w-full bg-input border border-border rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      >
                        <option value="Professor">Professor (Detailed)</option>
                        <option value="Notebook">Notebook (Conversational)</option>
                        <option value="Animated">Animated (Simple Concept)</option>
                        <option value="Revision">Revision (Fast Recall)</option>
                        <option value="Documentary">Documentary (Narrative)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <button 
                  onClick={handleGenerateVideo}
                  className="w-full py-4 rounded-xl bg-primary text-background font-extrabold text-base hover:bg-opacity-90 transition-all flex items-center justify-center gap-2 glow-primary"
                >
                  <Sparkles className="w-5 h-5" /> Generate Video
                </button>
              </div>
            </div>
          </div>
        )}

        {/* GENERATION PROGRESS PAGE */}
        {page === "generation" && (
          <div className="max-w-3xl mx-auto w-full">
            <div className="glass-panel p-8 rounded-3xl relative overflow-hidden">
              {/* Outer glow background decoration */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl"></div>
              
              <div className="flex justify-between items-start mb-8">
                <div>
                  <h2 className="text-2xl font-bold mb-1">Building Your Explainer Video</h2>
                  <p className="text-xs text-muted-foreground">This may take a few moments in low-resource fallback mode...</p>
                </div>
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold">
                  Job ID: {jobId || "connecting..."}
                </span>
              </div>

              {/* Error state */}
              {errorMsg ? (
                <div className="p-5 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-200 text-sm mb-6 flex gap-3">
                  <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="font-semibold mb-1">Pipeline Error</h4>
                    <p className="text-xs opacity-90">{errorMsg}</p>
                    <button 
                      onClick={() => setPage("create")}
                      className="mt-3 px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-xs font-semibold transition-all"
                    >
                      Go Back to Edit
                    </button>
                  </div>
                </div>
              ) : null}

              {/* Progress Slider */}
              <div className="mb-10">
                <div className="flex justify-between text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">
                  <span>Current: {jobStatus?.current_stage || "Initializing script..."}</span>
                  <span className="text-primary text-glow">{jobStatus?.progress || 0}%</span>
                </div>
                <div className="w-full h-2.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                  <div 
                    className="h-full bg-gradient-to-r from-primary to-purple-500 rounded-full transition-all duration-500" 
                    style={{ width: `${jobStatus?.progress || 0}%` }}
                  ></div>
                </div>
              </div>

              {/* Stage Progress Timeline */}
              <div className="space-y-4 mb-8">
                {[
                  { stage: "Analyzing document", label: "Read materials & extract concepts" },
                  { stage: "Creating script", label: "LLM pedagogy script structuring" },
                  { stage: "Planning scenes", label: "Storyboard visual-prompt blueprints" },
                  { stage: "narration", label: "Edge TTS audio narration generation", partialMatch: true },
                  { stage: "visual", label: "Dynamic image gradient diagram rendering", partialMatch: true },
                  { stage: "video", label: "FFmpeg clips compile & crossfades", partialMatch: true },
                  { stage: "Finalizing", label: "Stitch audio tracks & compile output track" }
                ].map((s, idx) => {
                  const currentStage = jobStatus?.current_stage || "";
                  
                  let isComplete = false;
                  let isActive = false;

                  if (s.partialMatch) {
                    isActive = currentStage.toLowerCase().includes(s.stage);
                    // Determine complete if progress is past certain thresholds
                    if (s.stage === "narration" && jobStatus && jobStatus.progress > 45) isComplete = true;
                    if (s.stage === "visual" && jobStatus && jobStatus.progress > 75) isComplete = true;
                    if (s.stage === "video" && jobStatus && jobStatus.progress > 90) isComplete = true;
                  } else {
                    isActive = currentStage === s.stage;
                    if (s.stage === "Analyzing document" && jobStatus && jobStatus.progress > 8) isComplete = true;
                    if (s.stage === "Creating script" && jobStatus && jobStatus.progress > 12) isComplete = true;
                    if (s.stage === "Planning scenes" && jobStatus && jobStatus.progress > 15) isComplete = true;
                    if (s.stage === "Finalizing" && jobStatus && jobStatus.progress === 100) isComplete = true;
                  }

                  return (
                    <div key={idx} className={`flex items-start gap-3 p-3 rounded-xl transition-all ${
                      isActive ? "bg-white/5 border border-white/10" : ""
                    }`}>
                      <div className="mt-0.5">
                        {isComplete ? (
                          <div className="w-5 h-5 rounded-full bg-green-500/20 border border-green-500 flex items-center justify-center">
                            <div className="w-2 h-2 rounded-full bg-green-500"></div>
                          </div>
                        ) : isActive ? (
                          <div className="w-5 h-5 rounded-full bg-primary/20 border border-primary flex items-center justify-center animate-pulse">
                            <div className="w-2 h-2 rounded-full bg-primary"></div>
                          </div>
                        ) : (
                          <div className="w-5 h-5 rounded-full bg-white/5 border border-white/10"></div>
                        )}
                      </div>
                      <div>
                        <p className={`text-sm font-semibold ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
                          {s.stage.charAt(0).toUpperCase() + s.stage.slice(1)}
                        </p>
                        <p className="text-xs text-muted-foreground opacity-80">{s.label}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Scene Storyboard Grid */}
              {script && script.scenes && (
                <div className="mt-8 pt-8 border-t border-border/60">
                  <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground mb-4">
                    Storyboard Scenes Queue ({script.scenes.length} Scenes Planned)
                  </h3>
                  
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {script.scenes.map((s) => {
                      const curScene = jobStatus?.current_scene || 0;
                      const isSceneComplete = curScene > s.id || (jobStatus && jobStatus.progress > 85);
                      const isSceneActive = curScene === s.id && jobStatus?.status === "generating";

                      return (
                        <div 
                          key={s.id}
                          className={`p-3 rounded-xl border text-left transition-all ${
                            isSceneComplete 
                              ? "bg-green-500/5 border-green-500/25" 
                              : isSceneActive 
                                ? "bg-primary/5 border-primary/40 shadow-sm" 
                                : "bg-white/5 border-border"
                          }`}
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-[10px] font-bold text-muted-foreground uppercase">Scene {s.id}</span>
                            {isSceneComplete ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                            ) : isSceneActive ? (
                              <RefreshCw className="w-3 h-3 text-primary animate-spin" />
                            ) : null}
                          </div>
                          <p className="text-xs font-semibold truncate">{s.title}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">{formatTime(s.duration)} narration</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Cancel Button */}
              <div className="mt-8 flex justify-end">
                <button 
                  onClick={handleCancelGeneration}
                  className="px-5 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all text-xs font-bold text-red-400"
                >
                  Cancel Generation
                </button>
              </div>
            </div>

            {/* REAL-TIME PIPELINE LOGS */}
            {jobStatus && jobStatus.logs && jobStatus.logs.length > 0 && (
              <div className="glass-panel p-5 rounded-2xl mt-6">
                <h4 className="font-bold text-xs uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                  <Info className="w-4 h-4 text-primary" /> Processing Log Output
                </h4>
                
                <div className="bg-black/40 border border-border rounded-xl p-4 font-mono text-[11px] text-zinc-400 h-40 overflow-y-auto space-y-1">
                  {jobStatus.logs.map((log, idx) => (
                    <div key={idx} className="leading-relaxed">
                      {log}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIDEO RESULT PAGE & SCENE EDITOR */}
        {page === "result" && jobId && script && (
          <div className="max-w-6xl mx-auto w-full">
            
            <div className="flex flex-col lg:flex-row gap-8 items-start">
              
              {/* Left Column: Player & Meta */}
              <div className="flex-1 w-full space-y-6">
                <div className="glass-panel p-4 rounded-3xl overflow-hidden shadow-2xl">
                  {/* HTML5 video player with subtitle support */}
                  <video 
                    controls 
                    className="w-full aspect-video bg-black rounded-2xl outline-none border border-white/5"
                    src={`${API_BASE}${jobStatus?.video_url || `/static/jobs/${jobId}/final_output_${jobId}.mp4`}`}
                    crossOrigin="anonymous"
                  >
                    <track 
                      label="English"
                      kind="subtitles"
                      srcLang="en"
                      src={`${API_BASE}/static/jobs/${jobId}/subtitles_${jobId}.vtt`}
                      default
                    />
                    Your browser does not support the video tag.
                  </video>
                </div>

                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h2 className="text-2xl font-bold">{script.title}</h2>
                      <p className="text-xs text-muted-foreground uppercase tracking-widest mt-1 font-semibold">
                        {script.scenes.length} Scenes • Duration: {formatTime(
                          script.scenes.reduce((acc, s) => acc + (s.actual_duration || s.duration), 0)
                        )}
                      </p>
                    </div>
                    
                    <a 
                      href={`${API_BASE}/api/video/${jobId}/download`}
                      download
                      className="px-5 py-3 rounded-xl bg-primary text-background font-bold text-sm hover:bg-opacity-90 transition-all flex items-center gap-2 glow-primary"
                    >
                      <Download className="w-4 h-4" /> Download MP4
                    </a>
                  </div>

                  <div className="border-t border-border/60 pt-4">
                    <h4 className="font-bold text-xs uppercase tracking-wider text-muted-foreground mb-1.5">Overview Summary</h4>
                    <p className="text-sm leading-relaxed text-zinc-300">{script.summary}</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button 
                    onClick={() => setPage("create")}
                    className="flex-1 py-3.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all text-sm font-bold flex items-center justify-center gap-2"
                  >
                    Create Another
                  </button>
                  <button 
                    onClick={handleGenerateVideo}
                    className="flex-1 py-3.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all text-sm font-bold flex items-center justify-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" /> Regenerate Video
                  </button>
                </div>
              </div>

              {/* Right Column: Storyboard scenes & Edit triggers */}
              <div className="w-full lg:w-[420px] shrink-0 space-y-6">
                <div className="glass-panel p-6 rounded-2xl h-[620px] flex flex-col justify-between">
                  <div className="overflow-y-auto pr-1 flex-grow">
                    <h3 className="font-bold text-base mb-4 flex items-center gap-2">
                      <Layers className="w-5 h-5 text-primary" /> Storyboard Timeline
                    </h3>
                    
                    <p className="text-xs text-muted-foreground mb-4">
                      Select any scene below to modify its title, narration voiceover, visual prompt cards, or keyword terms.
                    </p>

                    <div className="space-y-3">
                      {script.scenes.map((s) => (
                        <div 
                          key={s.id}
                          className="p-4 rounded-xl border border-border bg-white/[0.02] hover:bg-white/[0.05] transition-all text-left flex justify-between items-start cursor-pointer group"
                          onClick={() => openEditor(s)}
                        >
                          <div className="space-y-1 pr-4">
                            <span className="text-[9px] font-bold text-primary uppercase tracking-wider">Scene {s.id}</span>
                            <h4 className="font-semibold text-sm truncate w-[240px]">{s.title}</h4>
                            <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">{s.narration}</p>
                          </div>
                          
                          <button className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all shrink-0">
                            <Edit3 className="w-3.5 h-3.5 text-muted-foreground" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

            </div>

            {/* POPUP SCENE EDITOR MODAL */}
            {editingScene && (
              <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-6">
                <div className="glass-panel max-w-2xl w-full rounded-3xl p-8 relative overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-200">
                  <button 
                    onClick={() => setEditingScene(null)}
                    className="absolute top-6 right-6 p-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all"
                  >
                    <XCircle className="w-5 h-5 text-muted-foreground hover:text-foreground" />
                  </button>

                  <h3 className="font-bold text-xl mb-2 flex items-center gap-2">
                    <Edit3 className="w-5 h-5 text-primary" /> Edit Scene {editingScene.id}
                  </h3>
                  <p className="text-xs text-muted-foreground mb-6">
                    Modify the narration or drawing properties. Rebuilding compiles only this scene's assets, saving render time.
                  </p>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Scene Title</label>
                      <input 
                        type="text"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full bg-input border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Narration Text (Spoken Voiceover)</label>
                      <textarea 
                        rows={4}
                        value={editNarration}
                        onChange={(e) => setEditNarration(e.target.value)}
                        className="w-full bg-input border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary resize-none leading-relaxed"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">Visual Prompt Description (For PIL Slides / HF Gen)</label>
                      <input 
                        type="text"
                        value={editPrompt}
                        onChange={(e) => setEditPrompt(e.target.value)}
                        className="w-full bg-input border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">On-Screen Text Cards (Comma-separated lists)</label>
                      <input 
                        type="text"
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        placeholder="e.g. Encapsulation, Multiplexing, Layer Boundaries"
                        className="w-full bg-input border border-border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                  </div>

                  <div className="mt-8 flex justify-end gap-3">
                    <button 
                      onClick={() => setEditingScene(null)}
                      disabled={isUpdatingScene}
                      className="px-5 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all text-xs font-bold"
                    >
                      Discard Edits
                    </button>
                    <button 
                      onClick={handleRegenerateScene}
                      disabled={isUpdatingScene}
                      className="px-6 py-2.5 rounded-xl bg-primary text-background font-extrabold text-xs hover:bg-opacity-90 transition-all flex items-center gap-2 glow-primary disabled:opacity-50"
                    >
                      {isUpdatingScene ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Compiling changes...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" /> Rebuild Scene
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}

      </main>

      {/* FOOTER */}
      <footer className="border-t border-border/40 py-6 bg-background/30 backdrop-blur-sm mt-12 text-center text-xs text-muted-foreground">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>© {new Date().getFullYear()} StudyFlow AI. Local processing pipeline inspired by NotebookLM Video Overviews.</p>
          <div className="flex gap-4">
            <span className="hover:text-foreground cursor-pointer transition-colors">Documentation</span>
            <span>•</span>
            <span className="hover:text-foreground cursor-pointer transition-colors">Hugging Face Models</span>
            <span>•</span>
            <span className="hover:text-foreground cursor-pointer transition-colors">Edge TTS Voices</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
