import { useEffect, useState } from "react";
import {
  BrainCircuit,
  LayoutDashboard,
  Target,
  BookOpen,
  Route,
  Sparkles,
  ArrowRight,
  GraduationCap,
  LoaderCircle,
  AlertCircle,
  CheckCircle2,
  BriefcaseBusiness,
} from "lucide-react";
import "./index.css";

function apiFetch(url, options = {}) {
  const token = sessionStorage.getItem("skillpulse_token");

  const headers = {
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return fetch(url, {
    ...options,
    headers,
  });
}


const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

function SkillPulseApp({ user, onLogout }) {
  const [page, setPage] = useState("Dashboard");
  const [skills, setSkills] = useState("Python, SQL");
  const [careerGoal, setCareerGoal] = useState("");
  const [careerGoals, setCareerGoals] = useState([]);
  const [personalizedIDP, setPersonalizedIDP] = useState(null);
  const [completedSkills, setCompletedSkills] = useState([]);
  const [progressSaving, setProgressSaving] = useState(false);
  const [progressMessage, setProgressMessage] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [skillGaps, setSkillGaps] = useState([]);
  const [predictedSkill, setPredictedSkill] = useState("");
  const [roadmap, setRoadmap] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  
const [learningGoal, setLearningGoal] = useState("");
const [learningGoalPrediction, setLearningGoalPrediction] = useState("");
const [learningGoalLoading, setLearningGoalLoading] = useState(false);
const [learningGoalError, setLearningGoalError] = useState("");
const [skillRecommendations, setSkillRecommendations] = useState([]);
const [skillRecommendationLoading, setSkillRecommendationLoading] = useState(false);
const [skillRecommendationError, setSkillRecommendationError] = useState("");

  const menu = [
  { name: "Dashboard", icon: LayoutDashboard },
  { name: "Skill Analysis", icon: Target },
  { name: "Learning Goal Prediction", icon: BrainCircuit },
  { name: "Recommendations", icon: BookOpen },
  { name: "My IDP", icon: Route },
];


  useEffect(() => {
    let cancelled = false;

    async function loadCareerGoals() {
      try {
        const response = await fetch(`${API_URL}/api/career-goals`);
        if (!response.ok) {
          throw new Error(`Career list request returned HTTP ${response.status}`);
        }

        const data = await response.json();
        const goals = Array.isArray(data.career_goals)
          ? data.career_goals
          : [];

        if (cancelled) return;

        setCareerGoals(goals);
        setCareerGoal((current) =>
          goals.includes(current) ? current : (goals[0] || "")
        );
      } catch (err) {
        if (cancelled) return;
        console.error("Could not load career targets:", err);
        setError(
          "Could not load career targets. Make sure the Flask backend is running."
        );
      }
    }

    loadCareerGoals();
    return () => {
      cancelled = true;
    };
  }, []);

  const progressPlanKey = personalizedIDP
    ? `${personalizedIDP.career_goal}::${(personalizedIDP.current_skills || []).map((skill) => skill.trim().toLowerCase()).sort().join(",")}`
    : "";

  useEffect(() => {
    let cancelled = false;
    async function loadProgress() {
      if (!progressPlanKey) {
        setCompletedSkills([]);
        setProgressMessage("");
        return;
      }
      try {
        const response = await apiFetch(
  `${API_URL}/api/idp-progress/${encodeURIComponent(progressPlanKey)}`
);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        if (!cancelled) setCompletedSkills(Array.isArray(data.completed_skills) ? data.completed_skills : []);
      } catch (err) {
        if (!cancelled) {
          console.error("Could not load IDP progress:", err);
          setProgressMessage("Progress could not be loaded from the backend.");
        }
      }
    }
    loadProgress();
    return () => { cancelled = true; };
  }, [progressPlanKey]);

  async function toggleSkillCompletion(skill, checked) {
    const next = checked
      ? [...new Set([...completedSkills, skill])]
      : completedSkills.filter((item) => item !== skill);
    setCompletedSkills(next);
    setProgressSaving(true);
    setProgressMessage("");
    try {
      const response = await apiFetch(`${API_URL}/api/idp-progress`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    plan_key: progressPlanKey,
    completed_skills: next
  })
});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setProgressMessage("Progress saved.");
    } catch (err) {
      console.error("Could not save IDP progress:", err);
      setCompletedSkills(completedSkills);
      setProgressMessage(`Could not save progress: ${err.message}`);
    } finally {
      setProgressSaving(false);
    }
  }

  async function postData(endpoint, body) {
    const response = await apiFetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.error || `${endpoint} returned HTTP ${response.status}`
      );
    }

    return data;
  }
  
async function getPredictedSkillRecommendations() {
  const targetSkill = learningGoalPrediction.trim();

  if (!targetSkill) {
    setSkillRecommendationError("Please predict a target skill first.");
    return;
  }

  setSkillRecommendationLoading(true);
  setSkillRecommendationError("");
  setSkillRecommendations([]);
  setError("");
  setSuccess("");

  try {
    const data = await postData("/api/recommend-courses", {
      target_skill: targetSkill,
      top_k: 5,
    });

    setSkillRecommendations(
      Array.isArray(data.recommendations) ? data.recommendations : []
    );

    if (!data.recommendations?.length) {
      setSkillRecommendationError(
        `No matching courses were found for ${targetSkill}.`
      );
    }
  } catch (err) {
    setSkillRecommendationError(
      `Could not load recommendations: ${err.message}`
    );
  } finally {
    setSkillRecommendationLoading(false);
  }
}

async function predictLearningGoal(event) {
  event.preventDefault();

  if (!learningGoal.trim()) {
    setLearningGoalError("Please enter a learning goal.");
    return;
  }

  setLearningGoalLoading(true);
  setLearningGoalError("");
  setLearningGoalPrediction("");
  setError("");
  setSuccess("");

  try {
    const data = await postData(
      "/api/predict-from-learning-goal",
      { learning_goal: learningGoal.trim() }
    );

    const skill = String(
      data.predicted_target_skill || ""
    ).trim();

    if (!skill) {
      throw new Error("The model did not return a target skill.");
    }

    setLearningGoalPrediction(skill);
    setPredictedSkill(skill);
  } catch (err) {
    setLearningGoalError(`Prediction failed: ${err.message}`);
  } finally {
    setLearningGoalLoading(false);
  }
}

function addPredictedSkillToIDP() {
  const skill = learningGoalPrediction.trim();

  if (!skill || skillRecommendations.length === 0) {
    setSkillRecommendationError(
      "Predict a skill and load its courses first."
    );
    return;
  }

  if (!personalizedIDP || !analysis) {
    setSkillRecommendationError(
      "Please run Skill Analysis first to create your IDP."
    );
    setPage("Skill Analysis");
    return;
  }

  const existingRoadmap = personalizedIDP.idp_roadmap || [];

  if (
    existingRoadmap.some(
      (step) => step.skill?.toLowerCase() === skill.toLowerCase()
    )
  ) {
    setSkillRecommendationError(`${skill} is already in your IDP.`);
    return;
  }

  const newPhase = {
    skill,
    milestone: `Learn ${skill}`,
    learning_objective: `Develop practical skills in ${skill} using the recommended courses.`,
    duration_weeks: 1,
    recommended_courses: skillRecommendations,
  };

  const updatedIDP = {
    ...personalizedIDP,
    idp_roadmap: [...existingRoadmap, newPhase],
    skill_gaps: [...(personalizedIDP.skill_gaps || []), skill],
    course_recommendations: {
      ...(personalizedIDP.course_recommendations || {}),
      [skill]: skillRecommendations,
    },
  };

  setPersonalizedIDP(updatedIDP);
  setRoadmap(updatedIDP.idp_roadmap);

  setSkillGaps((previous) =>
    previous.some(
      (item) => item.toLowerCase() === skill.toLowerCase()
    )
      ? previous
      : [...previous, skill]
  );

  setSkillRecommendationError("");
  setSuccess(`${skill} and its courses were added to your IDP.`);
  setPage("My IDP");
}

  async function analyzeSkills(event) {
    if (event) event.preventDefault();

    const currentSkills = skills
      .split(",")
      .map((skill) => skill.trim())
      .filter(Boolean);

    if (!careerGoal) {
      setError("Please select a target career.");
      return;
    }

    if (currentSkills.length === 0) {
      setError("Please enter at least one current skill.");
      return;
    }

    setLoading(true);
    setError("");
    setSuccess("");
    setRecommendations([]);
    setSkillGaps([]);
    setPredictedSkill("");
    setRoadmap([]);
    setAnalysis(null);
    setPersonalizedIDP(null);

    try {
      // The backend looks up required skills automatically for this career,
      // calculates gaps, recommends courses for every gap, and builds the IDP.
      const data = await postData("/api/generate-personalized-idp", {
        career_goal: careerGoal,
        current_skills: currentSkills,
      });

      const gaps = data.skill_gaps || [];
      const allRecommendations = Object.entries(
        data.course_recommendations || {}
      ).flatMap(([skill, courses]) =>
        (courses || []).map((course) => ({ ...course, target_skill: skill }))
      );

      setPersonalizedIDP(data);
      setSkillGaps(gaps);
      setRoadmap(data.idp_roadmap || []);
      setRecommendations(allRecommendations);
      setPredictedSkill(gaps[0] || "");
      setAnalysis({
        skills: data.current_skills || currentSkills,
        requiredSkills: data.required_skills || [],
        careerGoal: data.career_goal || careerGoal,
        count: allRecommendations.length,
      });

      setSuccess(
        gaps.length
          ? `Career analysis complete. Found ${gaps.length} skill gap(s) and ${allRecommendations.length} course recommendation(s).`
          : "Career analysis complete. No skill gaps were identified."
      );
      setPage("Recommendations");
    } catch (err) {
      console.error("Personalized IDP error:", err);
      setError(
        `Could not analyze your career. Check that Flask is running and the personalized IDP endpoint is available. Details: ${err.message}`
      );
    } finally {
      setLoading(false);
    }
  }

  async function generateIDP() {
    setError("");
    setSuccess("");

    if (!analysis) {
      setError("Please analyze your skills first to generate your IDP.");
      setPage("Skill Analysis");
      return;
    }

    // The complete personalized plan was already returned by the analysis
    // endpoint. Display it without making a second, older IDP request.
    if (personalizedIDP) {
      setRoadmap(personalizedIDP.idp_roadmap || []);
      setPage("My IDP");
      setSuccess("Your personalized development plan is ready.");
      return;
    }

    setLoading(true);
    try {
      const data = await postData("/api/generate-personalized-idp", {
        career_goal: analysis.careerGoal,
        current_skills: analysis.skills,
      });
      setPersonalizedIDP(data);
      setSkillGaps(data.skill_gaps || []);
      setRoadmap(data.idp_roadmap || []);
      setSuccess("Your personalized development plan has been generated.");
      setPage("My IDP");
    } catch (err) {
      console.error("IDP error:", err);
      setError(`Could not generate your IDP. Details: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function navigate(name) {
    setPage(name);
    setError("");
    setSuccess("");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <BrainCircuit size={25} />
          </div>
          <div>
            <h2>SkillPulse</h2>
            <span>LEARN • GROW • ACHIEVE</span>
          </div>
        </div>

        <p className="menu-label">WORKSPACE</p>
        <nav className="sidebar-nav">
          {menu.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={`nav-item ${page === name ? "active" : ""}`}
              onClick={() => navigate(name)}
            >
              <Icon size={19} />
              <span>{name}</span>
              {page === name && <span className="nav-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="mini-avatar">S</div>
          <div>
            <strong>Student Workspace</strong>
            <span>Personal learning plan</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p>
            <h1>{page}</h1>
          </div>
          
<div className="topbar-actions">
  <span className="signed-in-name">
    {user?.name || user?.email || "Signed in"}
  </span>

  <div className="top-avatar">
    {(user?.name || "S").charAt(0).toUpperCase()}
  </div>

  <button
    type="button"
    className="signout-btn"
    onClick={onLogout}
  >
    Sign out
  </button>
</div>

        </header>

        {error && <ErrorMessage message={error} />}
        {success && (
          <div className="result-summary">
            <CheckCircle2 size={18} />
            {success}
          </div>
        )}

        {page === "Dashboard" && (
          <>
            <section className="welcome-panel">
              <div className="welcome-copy">
                <span className="pill">
                  <Sparkles size={14} />
                  AI-POWERED LEARNING
                </span>
                <h2>Build skills for the career you want.</h2>
                <p>
                  Discover skill gaps, explore relevant courses, and create a
                  learning plan designed around your career goals.
                </p>
                <button
                  className="primary-btn"
                  onClick={() => navigate("Skill Analysis")}
                >
                  Start skill analysis <ArrowRight size={17} />
                </button>
              </div>
              <div className="welcome-art">
                <BrainCircuit size={100} strokeWidth={1.1} />
              </div>
            </section>

            <section className="section-heading">
              <div>
                <h2>Your learning workspace</h2>
                <p>Tools to help you move toward your career goal.</p>
              </div>
            </section>

            <section className="feature-grid">
              <Feature
                icon={<Target />}
                number="01"
                title="Skill Gap Analysis"
                description="Compare your current skills with those required for your target career."
                onClick={() => navigate("Skill Analysis")}
              />
              <Feature
                icon={<BookOpen />}
                number="02"
                title="Course Recommendations"
                description="Find learning resources relevant to each skill gap."
                onClick={() => navigate("Recommendations")}
              />
              <Feature
                icon={<Route />}
                number="03"
                title="Individual Development Plan"
                description="Organize your learning into a structured development pathway."
                onClick={() => navigate("My IDP")}
              />
            </section>

            <section className="info-banner">
              <div className="banner-icon">
                <GraduationCap size={24} />
              </div>
              <div>
                <h3>Make your next learning step count</h3>
                <p>
                  Select a career and enter your current skills. SkillPulse
                  finds the required skills automatically.
                </p>
              </div>
              <button
                className="text-btn"
                onClick={() => navigate("Skill Analysis")}
              >
                Get started <ArrowRight size={16} />
              </button>
            </section>
          </>
        )}

        {page === "Skill Analysis" && (
          <section className="content-card">
            <div className="card-heading">
              <div className="large-icon">
                <Target size={24} />
              </div>
              <div>
                <h2>Analyze your skills</h2>
                <p>
                  Choose any career from the dataset. Required skills and gaps
                  will be calculated automatically.
                </p>
              </div>
            </div>

            <form onSubmit={analyzeSkills} className="analysis-form">
              <label htmlFor="career">Target career</label>
              <select
                id="career"
                value={careerGoal}
                onChange={(event) => setCareerGoal(event.target.value)}
                required
                disabled={careerGoals.length === 0}
              >
                {careerGoals.length === 0 ? (
                  <option value="">Loading careers...</option>
                ) : (
                  careerGoals.map((goal) => (
                    <option key={goal} value={goal}>
                      {goal}
                    </option>
                  ))
                )}
              </select>
              <span className="field-help">
                Career options are loaded from your dataset.
              </span>

              <label htmlFor="skills">Your current skills</label>
              <textarea
                id="skills"
                value={skills}
                onChange={(event) => setSkills(event.target.value)}
                placeholder="Example: Python, SQL, Excel"
                required
              />
              <span className="field-help">
                Separate multiple skills with commas.
              </span>

              <button
                className="primary-btn full-btn"
                disabled={loading || careerGoals.length === 0}
              >
                {loading ? (
                  <LoaderCircle className="spin" size={18} />
                ) : (
                  <Sparkles size={18} />
                )}
                {loading ? "Analyzing..." : "Analyze and generate IDP"}
              </button>
            </form>

            {analysis && personalizedIDP && (
              <div className="analysis-results">
                <h3>Career analysis: {analysis.careerGoal}</h3>
                <p>
                  {personalizedIDP.gap_count} skill gap(s) identified.
                  Estimated learning time:{" "}
                  {personalizedIDP.estimated_duration_weeks} weeks.
                </p>
                <h3>Required skills</h3>
                <div className="tag-row">
                  {(personalizedIDP.required_skills || []).map((skill) => (
                    <span className="course-tag" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>
                <h3>Skills to develop</h3>
                {skillGaps.length ? (
                  <div className="tag-row">
                    {skillGaps.map((skill) => (
                      <span className="course-tag" key={skill}>
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p>No skill gaps were identified.</p>
                )}
                <button className="primary-btn" onClick={() => navigate("My IDP")}>
                  View my IDP <ArrowRight size={17} />
                </button>
              </div>
            )}
          </section>
        )}
        {page === "Learning Goal Prediction" && (
  <section className="content-card">
    <div className="card-heading">
      <div className="large-icon">
        <BrainCircuit size={24} />
      </div>

      <div>
        <h2>Learning Goal Prediction</h2>
        <p>
          Enter a learning goal to identify the target skill
          recognized by the trained model.
        </p>
      </div>
    </div>

    <form
      className="analysis-form"
      onSubmit={predictLearningGoal}
    >
      <label htmlFor="learning-goal">
        Your learning goal
      </label>

      <textarea
        id="learning-goal"
        value={learningGoal}
        onChange={(event) =>
          setLearningGoal(event.target.value)
        }
        placeholder="Example: Develop Python for Data Scientist"
        required
      />

      <span className="field-help">
        Describe the skill you want to develop.
      </span>

      {learningGoalError && (
        <ErrorMessage message={learningGoalError} />
      )}

      <button
        type="submit"
        className="primary-btn full-btn"
        disabled={learningGoalLoading}
      >
        {learningGoalLoading ? (
          <LoaderCircle className="spin" size={18} />
        ) : (
          <Sparkles size={18} />
        )}

        {learningGoalLoading
          ? "Predicting..."
          : "Predict target skill"}
      </button>
    </form>

    {learningGoalPrediction && (
      <div className="analysis-results">
        <h3>Predicted target skill</h3>

        <div className="tag-row">
          <span className="course-tag">
            {learningGoalPrediction}
          </span>
        </div>

        <p className="field-help">
          The model uses the learning-goal text to produce
          this result. The result is not a guarantee of
          accurate prediction for unknown skills.
        </p>
        

      
        <button
          type="button"
          className="primary-btn"
          disabled={skillRecommendationLoading}
          onClick={getPredictedSkillRecommendations}
        >
          {skillRecommendationLoading
            ? "Finding courses..."
            : "Get Courses for Predicted Skill"}
          <ArrowRight size={17} />
        </button>

        {skillRecommendationError && (
          <ErrorMessage message={skillRecommendationError} />
        )}

        {skillRecommendations.length > 0 && (
          <div className="analysis-results">
            <h3>Courses for {learningGoalPrediction}</h3>
            {skillRecommendations.map((course, index) => (
              <article
                className="recommendation-item"
                key={course.resource_id || course.title || index}
              >
                <div className="course-number">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div className="course-details">
                  <h3>{course.title || "Recommended course"}</h3>
                  <p>{course.description || "Recommended learning resource"}</p>
                  <div className="tag-row">
                    {course.topic && <span className="course-tag">{course.topic}</span>}
                    {course.difficulty && <span className="course-tag">{course.difficulty}</span>}
                    {course.content_type && <span className="course-tag">{course.content_type}</span>}
                  </div>
                </div>
                {course.match_score !== undefined && (
                  <span className="similarity">
                    {Math.round(Number(course.match_score) * 100)}% match
                  </span>
                )}
              </article>
            ))}
            <button
              type="button"
              className="primary-btn"
              onClick={addPredictedSkillToIDP}
            >
              Add Predicted Skill to My IDP
              <ArrowRight size={17} />
            </button>
          </div>
        )}
      </div>
      
    )}

  </section>
)}

        {page === "Recommendations" && (
          <section className="content-card">
            <div className="card-heading">
              <div className="large-icon">
                <BookOpen size={24} />
              </div>
              <div>
                <h2>Recommended learning resources</h2>
                <p>
                  NLP-based course recommendations are grouped by each skill
                  gap in your selected career.
                </p>
              </div>
            </div>

            {!personalizedIDP ? (
              <div className="empty-state">
                <BookOpen size={38} />
                <h3>No recommendations yet</h3>
                <p>
                  Analyze your skills first to retrieve recommendations for
                  each missing skill.
                </p>
                <button
                  className="primary-btn"
                  onClick={() => navigate("Skill Analysis")}
                >
                  Analyze my skills <ArrowRight size={17} />
                </button>
              </div>
            ) : (
              <>
                <div className="result-summary">
                  <CheckCircle2 size={18} />
                  Career: {personalizedIDP.career_goal} ·{" "}
                  {recommendations.length} course recommendation(s)
                </div>

                {(personalizedIDP.skill_gaps || []).map((gap) => {
                  const courses =
                    personalizedIDP.course_recommendations?.[gap] || [];

                  return (
                    <section className="roadmap-list" key={gap}>
                      <h3>{gap}</h3>
                      {courses.length === 0 ? (
                        <p className="field-help">
                          No matching course was found for this skill yet.
                        </p>
                      ) : (
                        <div className="recommendation-list">
                          {courses.map((item, index) => (
                            <article
                              className="recommendation-item"
                              key={item.resource_id || `${gap}-${index}`}
                            >
                              <div className="course-number">
                                {String(index + 1).padStart(2, "0")}
                              </div>
                              <div className="course-details">
                                <h3>{item.title || "Recommended course"}</h3>
                                <p>
                                  {item.description ||
                                    "Recommended learning resource"}
                                </p>
                                <div className="tag-row">
                                  {item.topic && (
                                    <span className="course-tag">
                                      {item.topic}
                                    </span>
                                  )}
                                  {item.difficulty && (
                                    <span className="course-tag">
                                      {item.difficulty}
                                    </span>
                                  )}
                                  {item.content_type && (
                                    <span className="course-tag">
                                      {item.content_type}
                                    </span>
                                  )}
                                </div>
                              </div>
                              {item.match_score !== undefined && (
                                <span className="similarity">
                                  {Math.round(Number(item.match_score) * 100)}%
                                  {" "}match
                                </span>
                              )}
                            </article>
                          ))}
                        </div>
                      )}
                    </section>
                  );
                })}

                <button
                  className="primary-btn"
                  onClick={() => navigate("My IDP")}
                >
                  View my IDP <ArrowRight size={17} />
                </button>
              </>
            )}
          </section>
        )}

        {page === "My IDP" && (
          <section className="content-card">
            <div className="card-heading">
              <div className="large-icon">
                <Route size={24} />
              </div>
              <div>
                <h2>My Individual Development Plan</h2>
                <p>A structured pathway toward your career goal.</p>
              </div>
            </div>

            {!analysis || !personalizedIDP ? (
              <div className="empty-state">
                <Route size={38} />
                <h3>Your learning journey starts here</h3>
                <p>
                  Select a career and analyze your current skills to generate
                  your personalized development plan.
                </p>
                <button
                  className="primary-btn"
                  onClick={() => navigate("Skill Analysis")}
                >
                  Start skill analysis <ArrowRight size={17} />
                </button>
              </div>
            ) : (
              <div className="idp-content">
                <div className="idp-goal">
                  <BriefcaseBusiness size={22} />
                  <div>
                    <span>TARGET CAREER</span>
                    <h3>{personalizedIDP.career_goal}</h3>
                  </div>
                </div>

                <h3>Your current skills</h3>
                <div className="tag-row">
                  {(personalizedIDP.current_skills || []).map((skill) => (
                    <span className="course-tag" key={skill}>
                      {skill}
                    </span>
                  ))}
                </div>

                <h3>Skills to develop</h3>
                {skillGaps.length ? (
                  <div className="tag-row">
                    {skillGaps.map((skill) => (
                      <span className="course-tag" key={skill}>
                        {skill}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p>No skill gaps were identified.</p>
                )}

                <div className="result-summary">
                  Estimated duration:{" "}
                  {personalizedIDP.estimated_duration_weeks} weeks
                </div>

                <div className="result-summary">
                  <div style={{ width: "100%" }}>
                    <strong>Learning progress: {personalizedIDP.idp_roadmap?.length ? Math.round((completedSkills.length / personalizedIDP.idp_roadmap.length) * 100) : 0}%</strong>
                    <div style={{ height: 8, background: "var(--border-color, #e5e7eb)", borderRadius: 999, overflow: "hidden", marginTop: 8 }}>
                      <div style={{ height: "100%", width: `${personalizedIDP.idp_roadmap?.length ? (completedSkills.length / personalizedIDP.idp_roadmap.length) * 100 : 0}%`, background: "var(--primary-color, #2563eb)", transition: "width 180ms ease" }} />
                    </div>
                    <span className="field-help">{completedSkills.length} of {(personalizedIDP.idp_roadmap || []).length} learning phases completed.</span>
                    {progressSaving && <span className="field-help"> Saving progress…</span>}
                    {progressMessage && <span className="field-help"> {progressMessage}</span>}
                  </div>
                </div>

                <div className="roadmap-list">
                  <h3>Your learning roadmap</h3>
                  {(personalizedIDP.idp_roadmap || []).map((step, index) => (
                    <article
                      className="recommendation-item"
                      key={`${step.skill}-${index}`}
                    >
                      <div className="course-number">
                        {String(index + 1).padStart(2, "0")}
                      </div>
                      <div className="course-details">
                        <h3>{step.milestone}</h3>
                        <p>{step.learning_objective}</p>
                        <span className="course-tag">
                          {step.duration_weeks} weeks
                        </span>
                        <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, cursor: "pointer" }}>
                          <input
                            type="checkbox"
                            checked={completedSkills.includes(step.skill)}
                            onChange={(event) => toggleSkillCompletion(step.skill, event.target.checked)}
                          />
                          <span>{completedSkills.includes(step.skill) ? "Learning phase completed" : "Mark this phase as completed"}</span>
                        </label>
                        {(step.recommended_courses || []).length > 0 && (
                          <div className="tag-row">
                            <span className="field-help">
                              Suggested resource(s):{" "}
                              {step.recommended_courses
                                .map((course) => course.title)
                                .filter(Boolean)
                                .join(", ")}
                            </span>
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>

                <button
                  className="primary-btn"
                  onClick={() => navigate("Recommendations")}
                >
                  View recommended courses <ArrowRight size={17} />
                </button>
              </div>
            )}
          </section>
        )}

        <footer className="footer">
          SkillPulse <span>•</span> Personalized learning and development
        </footer>
      </main>
    </div>
  );
}

function Feature({ icon, number, title, description, onClick }) {
  return (
    <button className="feature-card" onClick={onClick}>
      <div className="feature-top">
        <div className="feature-icon">{icon}</div>
        <span>{number}</span>
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <div className="feature-link">
        Explore <ArrowRight size={16} />
      </div>
    </button>
  );
}

function ErrorMessage({ message }) {
  return (
    <div className="error-message">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem("skillpulse_token");

    if (!token) {
      setAuthChecked(true);
      return;
    }

    fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (!response.ok) {
          sessionStorage.removeItem("skillpulse_token");
          return null;
        }
        return response.json();
      })
      .then((data) => {
        if (data?.user) setUser(data.user);
      })
      .catch(() => {
        sessionStorage.removeItem("skillpulse_token");
      })
      .finally(() => setAuthChecked(true));
  }, []);

  async function handleLogout() {
    const token = sessionStorage.getItem("skillpulse_token");

    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: "POST",
        headers: token
          ? { Authorization: `Bearer ${token}` }
          : {},
      });
    } catch (error) {
      console.error("Logout request failed:", error);
    }

    sessionStorage.removeItem("skillpulse_token");
    setUser(null);
  }

  if (!authChecked) {
    return <div className="auth-loading">Loading SkillPulse...</div>;
  }

  if (!user) {
    return (
      <AuthScreen
        onAuthenticated={(nextUser, token) => {
          sessionStorage.setItem("skillpulse_token", token);
          setUser(nextUser);
        }}
      />
    );
  }

  return <SkillPulseApp user={user} onLogout={handleLogout} />;
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/auth/${mode === "login" ? "login" : "register"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name.trim(),
            email: email.trim(),
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Authentication failed.");
      }

      if (!data.token || !data.user) {
        throw new Error("The server did not return a user and token.");
      }

      onAuthenticated(data.user, data.token);
    } catch (err) {
      setError(err.message || "Could not connect to the backend.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-logo">
          <BrainCircuit size={32} />
        </div>

        <p className="auth-eyebrow">YOUR PERSONAL LEARNING SPACE</p>
        <h1>SkillPulse</h1>
        <p className="auth-description">
          Learn new skills. Build your future. Achieve your career goals.
        </p>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === "login" ? "selected" : ""}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Sign in
          </button>

          <button
            type="button"
            className={mode === "register" ? "selected" : ""}
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            Create account
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          <h2>
            {mode === "login" ? "Welcome back" : "Create your account"}
          </h2>

          {mode === "register" && (
            <label>
              Full name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
                maxLength={80}
                placeholder="Your name"
              />
            </label>
          )}

          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              placeholder="you@example.com"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              minLength={mode === "register" ? 10 : 1}
              maxLength={128}
              required
              placeholder={
                mode === "register"
                  ? "At least 10 characters"
                  : "Your password"
              }
            />
          </label>

          {error && <div className="auth-error">{error}</div>}

          <button className="auth-submit" type="submit" disabled={busy}>
            {busy
              ? "Please wait..."
              : mode === "login"
                ? "Sign in to SkillPulse"
                : "Create my account"}
            {!busy && <ArrowRight size={18} />}
          </button>
        </form>
      </section>
    </main>
  );
}
