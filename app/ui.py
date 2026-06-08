from __future__ import annotations


def render_test_ui() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FastAPI With LangGraph Tester</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --line: #d9dee7;
      --text: #18202c;
      --muted: #657184;
      --accent: #0f6b5f;
      --accent-dark: #0a5148;
      --danger: #a33a32;
      --code: #111827;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 15px;
    }

    header {
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }

    .shell {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      min-height: 68px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 720;
      letter-spacing: 0;
    }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    main {
      padding: 24px 0 32px;
    }

    .workspace {
      display: grid;
      grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }

    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 16px;
      border-bottom: 1px solid var(--line);
    }

    h2 {
      margin: 0;
      font-size: 15px;
      font-weight: 680;
      letter-spacing: 0;
    }

    .method {
      display: inline-flex;
      align-items: center;
      height: 24px;
      padding: 0 8px;
      border-radius: 4px;
      background: #e7f4f0;
      color: var(--accent-dark);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 12px;
      font-weight: 700;
    }

    form,
    .response-body {
      padding: 16px;
    }

    label {
      display: block;
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }

    textarea,
    input,
    select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfd;
      color: var(--text);
      font: inherit;
      letter-spacing: 0;
    }

    textarea {
      min-height: 128px;
      resize: vertical;
      padding: 11px 12px;
      line-height: 1.45;
    }

    input,
    select {
      height: 40px;
      padding: 0 10px;
    }

    .field {
      margin-bottom: 14px;
    }

    .field-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    button,
    .link-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 38px;
      padding: 0 12px;
      border-radius: 6px;
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--text);
      font: inherit;
      font-size: 14px;
      font-weight: 650;
      text-decoration: none;
      cursor: pointer;
    }

    button.primary {
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
    }

    button.primary:hover {
      background: var(--accent-dark);
    }

    button:disabled {
      cursor: progress;
      opacity: 0.7;
    }

    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 16px;
    }

    .status-line {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .human-panel {
      margin-bottom: 14px;
      border: 1px solid #d4b06a;
      border-radius: 8px;
      background: #fff8e8;
      padding: 14px;
    }

    .human-panel.hidden {
      display: none;
    }

    .human-panel h3 {
      margin: 0 0 12px;
      font-size: 14px;
      letter-spacing: 0;
    }

    .human-question {
      margin-bottom: 12px;
    }

    .human-question:last-child {
      margin-bottom: 0;
    }

    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfd;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }

    .metric strong {
      display: block;
      margin-top: 4px;
      font-size: 14px;
      word-break: break-word;
    }

    pre {
      min-height: 360px;
      max-height: 640px;
      margin: 0;
      overflow: auto;
      border-radius: 6px;
      background: var(--code);
      color: #eef2f7;
      padding: 14px;
      white-space: pre-wrap;
      word-break: break-word;
      font: 13px/1.5 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    .error {
      color: var(--danger);
    }

    @media (max-width: 860px) {
      .workspace {
        grid-template-columns: 1fr;
      }

      .topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 14px 0;
      }

      .status-line,
      .field-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="shell topbar">
      <h1>FastAPI With LangGraph Tester</h1>
      <div class="top-actions">
        <a class="link-button" href="/docs">Swagger</a>
        <button type="button" id="healthButton">Health</button>
        <button type="button" id="graphButton">Graph</button>
      </div>
    </div>
  </header>

  <main class="shell">
    <div class="workspace">
      <section aria-labelledby="request-title">
        <div class="panel-head">
          <h2 id="request-title">Agent Request</h2>
          <span class="method">POST /agent/run</span>
        </div>
        <form id="agentForm">
          <div class="field">
            <label for="query">Query</label>
            <textarea id="query" name="query" required>Create a FastAPI and LangGraph project, explain the files, document the nodes and edges, and show how the agent API works.</textarea>
          </div>
          <div class="field-row">
            <div class="field">
              <label for="maxRevisions">Max revisions</label>
              <input id="maxRevisions" name="maxRevisions" type="number" min="0" max="5" value="2">
            </div>
            <div class="field">
              <label for="scenario">Scenario</label>
              <input id="scenario" name="scenario" value="local-ui-test">
            </div>
          </div>
          <div class="field">
            <label for="context">Context JSON</label>
            <textarea id="context" name="context">{
  "source": "test-ui",
  "priority": "learning"
}</textarea>
          </div>
          <div class="button-row">
            <button class="primary" type="submit" id="runButton">Run agent</button>
            <button type="button" id="productSampleButton">Load product sample</button>
            <button type="button" id="sampleButton">Load calculator sample</button>
            <button type="button" id="clearButton">Clear response</button>
          </div>
        </form>
      </section>

      <section aria-labelledby="response-title">
        <div class="panel-head">
          <h2 id="response-title">API Response</h2>
          <span class="method" id="methodBadge">READY</span>
        </div>
        <div class="response-body">
          <div class="status-line">
            <div class="metric">
              <span>Status</span>
              <strong id="statusValue">idle</strong>
            </div>
            <div class="metric">
              <span>Route count</span>
              <strong id="routeCount">0</strong>
            </div>
            <div class="metric">
              <span>Trace count</span>
              <strong id="traceCount">0</strong>
            </div>
          </div>
          <div class="human-panel hidden" id="humanPanel">
            <h3>Human input required</h3>
            <div id="questionList"></div>
            <div class="button-row">
              <button class="primary" type="button" id="continueButton">Continue with answers</button>
            </div>
          </div>
          <pre id="output">Submit a request to create a new agent run.</pre>
        </div>
      </section>
    </div>
  </main>

  <script>
    const form = document.querySelector("#agentForm");
    const query = document.querySelector("#query");
    const context = document.querySelector("#context");
    const scenario = document.querySelector("#scenario");
    const maxRevisions = document.querySelector("#maxRevisions");
    const output = document.querySelector("#output");
    const statusValue = document.querySelector("#statusValue");
    const routeCount = document.querySelector("#routeCount");
    const traceCount = document.querySelector("#traceCount");
    const methodBadge = document.querySelector("#methodBadge");
    const runButton = document.querySelector("#runButton");
    const humanPanel = document.querySelector("#humanPanel");
    const questionList = document.querySelector("#questionList");
    const continueButton = document.querySelector("#continueButton");

    let latestQuestions = [];

    function setOutput(data, method) {
      methodBadge.textContent = method;
      output.classList.remove("error");
      output.textContent = JSON.stringify(data, null, 2);
      statusValue.textContent = data.status || "ok";
      routeCount.textContent = Array.isArray(data.route_history) ? data.route_history.length : "0";
      traceCount.textContent = Array.isArray(data.trace) ? data.trace.length : "0";
      renderHumanQuestions(data);
    }

    function setError(error, method) {
      methodBadge.textContent = method;
      output.classList.add("error");
      output.textContent = error.message || String(error);
      statusValue.textContent = "error";
      routeCount.textContent = "0";
      traceCount.textContent = "0";
      hideHumanQuestions();
    }

    async function readJson(response) {
      const text = await response.text();
      try {
        return text ? JSON.parse(text) : {};
      } catch {
        return { raw: text };
      }
    }

    function readContextValue() {
      try {
        return JSON.parse(context.value || "{}");
      } catch {
        throw new Error("Context JSON is invalid.");
      }
    }

    function writeContextValue(value) {
      context.value = JSON.stringify(value, null, 2);
    }

    function createQuestionControl(question) {
      if (question.type === "choice" || question.type === "yes_no") {
        const select = document.createElement("select");
        select.dataset.questionId = question.id;
        for (const option of question.options || []) {
          const item = document.createElement("option");
          item.value = option;
          item.textContent = option;
          select.appendChild(item);
        }
        return select;
      }

      const input = document.createElement("input");
      input.dataset.questionId = question.id;
      input.placeholder = "Type your answer";
      return input;
    }

    function renderHumanQuestions(data) {
      latestQuestions = Array.isArray(data.human_questions) ? data.human_questions : [];
      questionList.replaceChildren();

      if (data.status !== "needs_input" || latestQuestions.length === 0) {
        hideHumanQuestions();
        return;
      }

      for (const question of latestQuestions) {
        const wrapper = document.createElement("div");
        wrapper.className = "human-question";

        const label = document.createElement("label");
        label.textContent = question.question;

        const control = createQuestionControl(question);
        control.required = question.required !== false;

        wrapper.appendChild(label);
        wrapper.appendChild(control);
        questionList.appendChild(wrapper);
      }

      humanPanel.classList.remove("hidden");
    }

    function hideHumanQuestions() {
      latestQuestions = [];
      questionList.replaceChildren();
      humanPanel.classList.add("hidden");
    }

    function collectHumanAnswers() {
      const answers = {};
      for (const question of latestQuestions) {
        const control = questionList.querySelector(`[data-question-id="${question.id}"]`);
        if (control && control.value) {
          answers[question.id] = control.value;
        }
      }
      return answers;
    }

    async function runAgent(extraHumanAnswers = {}) {
      runButton.disabled = true;
      continueButton.disabled = true;
      statusValue.textContent = "running";
      methodBadge.textContent = "POST";

      try {
        const contextValue = readContextValue();
        contextValue.scenario = scenario.value;
        if (Object.keys(extraHumanAnswers).length > 0) {
          contextValue.human_answers = {
            ...(contextValue.human_answers || {}),
            ...extraHumanAnswers
          };
          writeContextValue(contextValue);
        }

        const response = await fetch("/agent/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.value,
            context: contextValue,
            max_revisions: Number(maxRevisions.value || 0)
          })
        });
        const data = await readJson(response);
        if (!response.ok) {
          throw new Error(JSON.stringify(data, null, 2));
        }
        setOutput(data, "POST");
      } catch (error) {
        setError(error, "POST");
      } finally {
        runButton.disabled = false;
        continueButton.disabled = false;
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      await runAgent();
    });

    document.querySelector("#healthButton").addEventListener("click", async () => {
      try {
        const response = await fetch("/health");
        setOutput(await readJson(response), "GET");
      } catch (error) {
        setError(error, "GET");
      }
    });

    document.querySelector("#graphButton").addEventListener("click", async () => {
      try {
        const response = await fetch("/agent/graph");
        setOutput(await readJson(response), "GET");
      } catch (error) {
        setError(error, "GET");
      }
    });

    document.querySelector("#sampleButton").addEventListener("click", () => {
      query.value = "Calculate 12 * (4 + 3), explain the result, and show which agent route was used.";
      context.value = JSON.stringify({ source: "test-ui", priority: "calculation-demo" }, null, 2);
      scenario.value = "calculator-sample";
      hideHumanQuestions();
    });

    document.querySelector("#productSampleButton").addEventListener("click", () => {
      query.value = "Find a product under 50 dollars.";
      context.value = JSON.stringify({ source: "test-ui", priority: "human-in-loop-demo" }, null, 2);
      scenario.value = "product-human-input";
      hideHumanQuestions();
    });

    continueButton.addEventListener("click", async () => {
      await runAgent(collectHumanAnswers());
    });

    document.querySelector("#clearButton").addEventListener("click", () => {
      methodBadge.textContent = "READY";
      statusValue.textContent = "idle";
      routeCount.textContent = "0";
      traceCount.textContent = "0";
      output.classList.remove("error");
      output.textContent = "Submit a request to create a new agent run.";
      hideHumanQuestions();
    });
  </script>
</body>
</html>
"""
