
const DAYS = [
  { label: "Monday", api: "Mon" },
  { label: "Tuesday", api: "Tue" },
  { label: "Wednesday", api: "Wed" },
  { label: "Thursday", api: "Thu" },
  { label: "Friday", api: "Fri" },
  { label: "Saturday", api: "Sat" },
  { label: "Sunday", api: "Sun" }
];

const HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16];

const state = {
  page: "login",
  role: null,
  email: "",
  nav: "dashboard",
  availability: new Set(),
  rules: { max_hours: 30, max_per_slot: 3 },
  employees: [],
  demand: {},
  schedules: [],
  scheduleStudentFilters: {}
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const fetchOptions = {
    method: options.method || "GET",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" }
  };

  if (options.body !== undefined) {
    fetchOptions.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, fetchOptions);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }

  return data;
}

function render() {
  const app = document.getElementById("app");

  if (state.page === "login") {
    app.innerHTML = loginPage();
  } else if (state.page === "signup") {
    app.innerHTML = signupPage();
  } else {
    app.innerHTML = dashboardShell();
  }
}

function loginPage() {
  return `
    <main class="login-page">
      <section class="login-card">
        <div class="logo">US</div>
        <h1>University Scheduler</h1>
        <p class="subtitle">Sign in with your university account to manage availability or scheduling.</p>

        <form onsubmit="return login(event)">
          <label class="field-label" for="email">School Email</label>
          <input id="email" type="email" placeholder="name@bridgew.edu" autocomplete="username" value="${escapeHtml(state.email)}" required>

          <label class="field-label" for="password" style="margin-top:16px;">Password</label>
          <input id="password" type="password" placeholder="Enter your password" autocomplete="current-password" required>

          <p id="loginError" class="form-error"></p>
          <button class="primary" style="margin-top:24px" type="submit">Login</button>
        </form>

        <p style="text-align:center;margin:20px 0 0;color:var(--muted);font-size:13px;">
          Students don't have an account?
          <button type="button" onclick="showSignup()" class="text-button">Sign up</button>
        </p>
      </section>
    </main>`;
}

function signupPage() {
  return `
    <main class="login-page">
      <section class="login-card">
        <div class="logo">US</div>
        <h1>Create Student Account</h1>
        <p class="subtitle">Create a student account to submit your weekly availability.</p>

        <form onsubmit="return signup(event)">
          <label class="field-label" for="signupEmail">Student Email</label>
          <input id="signupEmail" type="email" placeholder="student@bridgew.edu" autocomplete="username" required>

          <label class="field-label" for="signupPassword" style="margin-top:16px;">Password</label>
          <input id="signupPassword" type="password" placeholder="Create a password" autocomplete="new-password" required>

          <label class="field-label" for="signupConfirm" style="margin-top:16px;">Confirm Password</label>
          <input id="signupConfirm" type="password" placeholder="Confirm your password" autocomplete="new-password" required>

          <p id="signupError" class="form-error"></p>
          <button class="primary" style="margin-top:24px" type="submit">Create Account</button>
        </form>

        <p style="text-align:center;margin:20px 0 0;color:var(--muted);font-size:13px;">
          Already have an account?
          <button type="button" onclick="backToLogin()" class="text-button">Back to Login</button>
        </p>
      </section>
    </main>`;
}

function showSignup() {
  state.page = "signup";
  render();
}

function backToLogin() {
  state.page = "login";
  render();
}

async function login(event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim().toLowerCase();
  const password = document.getElementById("password").value;
  const error = document.getElementById("loginError");

  error.textContent = "";
  error.style.display = "none";

  try {
    const data = await api("/api/login", {
      method: "POST",
      body: { email, password }
    });

    state.email = data.email;
    state.role = data.role;
    state.page = "app";
    state.nav = data.role === "faculty" ? "dashboard" : "availability";

    await loadCurrentPageData();
    render();
  } catch (err) {
    error.textContent = err.message;
    error.style.display = "block";
  }

  return false;
}

async function signup(event) {
  event.preventDefault();

  const email = document.getElementById("signupEmail").value.trim().toLowerCase();
  const password = document.getElementById("signupPassword").value;
  const confirm = document.getElementById("signupConfirm").value;
  const error = document.getElementById("signupError");

  error.textContent = "";
  error.style.display = "none";

  if (password !== confirm) {
    error.textContent = "Passwords do not match.";
    error.style.display = "block";
    return false;
  }

  try {
    await api("/api/signup", {
      method: "POST",
      body: { email, password }
    });

    state.email = email;
    state.page = "login";
    render();

    const loginEmail = document.getElementById("email");
    if (loginEmail) loginEmail.value = email;

    const loginError = document.getElementById("loginError");
    if (loginError) {
      loginError.textContent = "Account created. You can log in now.";
      loginError.className = "form-success";
      loginError.style.display = "block";
    }
  } catch (err) {
    error.textContent = err.message;
    error.style.display = "block";
  }

  return false;
}

async function logout() {
  try {
    await api("/api/logout", { method: "POST" });
  } catch (err) {
    console.error(err);
  }

  state.page = "login";
  state.role = null;
  state.email = "";
  state.availability = new Set();
  state.employees = [];
  state.demand = {};
  state.schedules = [];
  state.scheduleStudentFilters = {};
  render();
}

function dashboardShell() {
  const faculty = state.role === "faculty";
  const active = state.nav;

  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">University Scheduler</div>
        <nav class="nav">
          ${faculty ? `
            <button class="${active === "dashboard" ? "active" : ""}" onclick="navigate('dashboard')">Dashboard</button>
            <button class="${active === "employees" ? "active" : ""}" onclick="navigate('employees')">Employees</button>
            <button class="${active === "availability" ? "active" : ""}" onclick="navigate('availability')">Availability</button>
            <button class="${active === "schedule" ? "active" : ""}" onclick="navigate('schedule')">Schedule</button>
          ` : `
            <button class="${active === "availability" ? "active" : ""}" onclick="navigate('availability')">Availability</button>
            <button class="${active === "myschedule" ? "active" : ""}" onclick="navigate('myschedule')">My Schedule</button>
          `}
        </nav>
        <button class="logout" onclick="logout()">Log out</button>
      </aside>

      <main class="main">
        <header class="topbar">
          <div><strong>${faculty ? "Faculty Portal" : "Student Portal"}</strong></div>
          <div class="user">
            <span>${escapeHtml(state.email)}</span>
            <div class="avatar">${escapeHtml((state.email || "U").charAt(0).toUpperCase())}</div>
          </div>
        </header>
        <section class="content">
          ${faculty ? employerPage(active) : employeePage(active)}
        </section>
      </main>
    </div>`;
}

async function navigate(page) {
  state.nav = page;
  await loadCurrentPageData();
  render();
}

async function loadCurrentPageData() {
  if (state.role === "student") {
    if (state.nav === "availability") await loadStudentAvailability();
    return;
  }

  if (state.role === "faculty") {
    if (state.nav === "dashboard" || state.nav === "employees") {
      await loadFacultyEmployees();
    }
    if (state.nav === "availability") {
      await loadFacultyDemand();
    }
    if (state.nav === "dashboard" || state.nav === "availability" || state.nav === "schedule") {
      await loadFacultyRules();
    }
  }
}

function hourLabel(hour) {
  const end = hour + 1;
  const fmt = (h) => h === 12 ? "12 PM" : h > 12 ? `${h - 12} PM` : `${h} AM`;
  return `${fmt(hour)}–${fmt(end)}`;
}

function employeePage(page) {
  if (page === "myschedule") {
    return `
      <div class="page-title">
        <div><h1>My Schedule</h1><p class="muted">Your assigned work schedule will appear here.</p></div>
      </div>
      <div class="card empty-state">
        <h3>No schedule generated yet</h3>
        <p class="muted">Once your supervisor generates the schedule, your assigned time slots will appear here.</p>
      </div>`;
  }

  return `
    <div class="page-title">
      <div><h1>My Availability</h1><p class="muted">Select every time slot when you are available to work.</p></div>
      <span class="badge">8 AM – 5 PM</span>
    </div>
    <p class="mobile-note">Tap a cell to mark yourself available.</p>
    <div class="card grid-card">
      <table class="availability">
        <thead>
          <tr><th>Time</th>${DAYS.map(day => `<th>${day.label}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${HOURS.map(hour => `
            <tr>
              <td class="time">${hourLabel(hour)}</td>
              ${DAYS.map(day => {
                const key = `${day.api}-${hour}`;
                const selected = state.availability.has(key);
                return `<td><button class="slot ${selected ? "selected" : ""}" onclick="toggleSlot('${day.api}', ${hour})" aria-label="${day.label} ${hourLabel(hour)}" aria-pressed="${selected}"></button></td>`;
              }).join("")}
            </tr>`).join("")}
        </tbody>
      </table>
      <div class="actions availability-actions">
        <div class="muted selection-count">Selected: <strong>${state.availability.size}</strong> hours</div>
        <div>
          <button class="secondary" onclick="clearAvailability()">Clear All</button>
          <button class="primary action-button" onclick="saveAvailability()">Save Availability</button>
        </div>
      </div>
      <p id="studentSaveMessage" class="inline-message"></p>
    </div>`;
}

function toggleSlot(day, hour) {
  const key = `${day}-${hour}`;
  if (state.availability.has(key)) state.availability.delete(key);
  else state.availability.add(key);
  render();
}

function clearAvailability() {
  state.availability.clear();
  render();
}

async function loadStudentAvailability() {
  const data = await api("/api/availability");
  state.availability = new Set(
    (data.slots || []).map(slot => `${slot.day}-${Number(slot.hour)}`)
  );
}

async function saveAvailability() {
  const message = document.getElementById("studentSaveMessage");
  const button = document.querySelector(".availability-actions .action-button");

  if (button) {
    button.disabled = true;
    button.textContent = "Saving...";
  }

  try {
    const slots = Array.from(state.availability).map(key => {
      const [day, hour] = key.split("-");
      return { day, hour: Number(hour) };
    });

    const result = await api("/api/availability", {
      method: "PUT",
      body: { slots }
    });

    await loadStudentAvailability();
    render();

    const success = document.getElementById("studentSaveMessage");
    if (success) {
      success.textContent = `Saved ${result.count} hour${result.count === 1 ? "" : "s"}.`;
      success.className = "inline-message success";
    }
  } catch (err) {
    if (message) {
      message.textContent = err.message;
      message.className = "inline-message error";
    } else {
      alert(`Could not save your availability: ${err.message}`);
    }
  } finally {
    const currentButton = document.querySelector(".availability-actions .action-button");
    if (currentButton) {
      currentButton.disabled = false;
      currentButton.textContent = "Save Availability";
    }
  }
}

function employerPage(page) {
  if (page === "employees") return employeesPage();
  if (page === "availability") return availabilityOverviewPage();
  if (page === "schedule") return schedulePage();
  return dashboardPage();
}

function employeesPage() {
  const employees = state.employees || [];

  return `
    <div class="page-title">
      <div>
        <h1>Employees</h1>
        <p class="muted">Review each student's weekly availability.</p>
      </div>
    </div>

    <div class="employee-calendar-list">

      ${
        employees.length
          ? employees.map(employee => {
              const availability = employee.availability || [];
              const availabilitySet = new Set(
                availability.map(slot => `${slot.day}-${Number(slot.hour)}`)
              );

              const hours = Number(employee.availability_count) || 0;

              return `
                <div class="card employee-calendar-card">
                  <div class="employee-header">
                    <div>
                      <h2>${escapeHtml(employee.email)}</h2>
                      <p class="muted">
                        ${hours} hour${hours === 1 ? "" : "s"} available
                      </p>
                    </div>

                    <span class="badge">
                      ${hours > 0 ? "Submitted" : "Pending"}
                    </span>
                  </div>

                  <div class="employee-calendar-wrapper">
                    <table class="employee-calendar">
                      <thead>
                        <tr>
                          <th class="calendar-time-header">Time</th>
                          ${DAYS.map(day => `
                            <th>${day.label}</th>
                          `).join("")}
                        </tr>
                      </thead>

                      <tbody>
                        ${HOURS.map(hour => `
                          <tr>
                            <td class="calendar-time">
                              ${hourLabel(hour)}
                            </td>

                            ${DAYS.map(day => {
                              const key = `${day.api}-${hour}`;
                              const available = availabilitySet.has(key);

                              return `
                                <td class="${available ? "employee-available" : "employee-unavailable"}">
                                  ${
                                    available
                                      ? `<span class="availability-check">✓</span>`
                                      : `<span class="availability-dash">—</span>`
                                  }
                                </td>
                              `;
                            }).join("")}
                          </tr>
                        `).join("")}
                      </tbody>
                    </table>
                  </div>

                  <div class="employee-calendar-legend">
                    <span>
                      <i class="legend-box available"></i>
                      Available
                    </span>
                    <span>
                      <i class="legend-box unavailable"></i>
                      Not Available
                    </span>
                  </div>
                </div>
              `;
            }).join("")
          : `
            <div class="card empty-state">
              <h3>No students have registered yet.</h3>
              <p class="muted">
                Students will appear here after creating an account.
              </p>
            </div>
          `
      }
    </div>
  `;
}

function availabilityOverviewPage() {
  const max = Number(state.rules.max_per_slot) || 1;

  return `
    <div class="page-title">
      <div><h1>Availability Overview</h1><p class="muted">A live summary of submitted student availability.</p></div>
      <span class="badge">Limit: ${max} / slot</span>
    </div>
    <div class="card grid-card">
      <table class="availability faculty-grid">
        <thead><tr><th>Time</th>${DAYS.map(day => `<th>${day.label}</th>`).join("")}</tr></thead>
        <tbody>
          ${HOURS.map(hour => `
            <tr>
              <td class="time">${hourLabel(hour)}</td>
              ${DAYS.map(day => {
                const count = Number(state.demand[`${day.api}-${hour}`] || 0);
                const status = count > max ? "demand-over" : count === max && count > 0 ? "demand-full" : "demand-ok";
                return `<td class="${status}"><span class="demand-number">${count}</span></td>`;
              }).join("")}
            </tr>`).join("")}
        </tbody>
      </table>
      <div class="demand-legend">
        <span><i class="swatch under"></i>Under limit</span>
        <span><i class="swatch at"></i>At limit</span>
        <span><i class="swatch over"></i>Over limit</span>
      </div>
    </div>`;
}

function dashboardPage() {
  const employees = state.employees || [];
  const participating = employees.length;
  const submitted = employees.filter(e => Number(e.availability_count) > 0).length;

  return `
    <div class="page-title">
      <div><h1>Dashboard</h1><p class="muted">Configure scheduling rules for your students.</p></div>
    </div>
    <div class="stats">
      <div class="card"><div class="stat-label">Students</div><div class="stat-value">${participating}</div><div class="muted">participating</div></div>
      <div class="card"><div class="stat-label">Availability Submitted</div><div class="stat-value">${submitted}</div><div class="muted">of ${participating} students</div></div>
      <div class="card"><div class="stat-label">Schedule Status</div><div class="stat-value status-value">Not Generated</div><div class="muted">ready when scheduling is implemented</div></div>
    </div>
    <div class="card">
      <h2>Scheduling Constraints</h2>
      <p class="muted">Set the rules that the scheduling system should follow.</p>
      <div class="form-grid">
        <div class="form-group">
          <label class="field-label" for="maxHours">Maximum Total Hours for All Employees</label>
          <input id="maxHours" type="number" min="1" value="${Number(state.rules.max_hours) || 30}" />
          <div class="help">Maximum combined number of work hours across all employees.</div>
        </div>
        <div class="form-group">
          <label class="field-label" for="maxEmployees">Maximum Employees per Time Slot</label>
          <input id="maxEmployees" type="number" min="1" value="${Number(state.rules.max_per_slot) || 3}" />
          <div class="help">Maximum number of students allowed in one time slot.</div>
        </div>
      </div>
      <div class="actions"><button id="saveConstraintsButton" class="primary action-button" type="button" onclick="saveConstraints()">Save Constraints</button></div>
      <p id="rulesMessage" class="inline-message"></p>
    </div>`;
}

function scheduleTimeLabel(hour) {
  if (hour === 12) return "12 PM";
  if (hour > 12) return `${hour - 12} PM`;
  return `${hour} AM`;
}

function studentColor(email) {
  let hash = 0;

  for (let i = 0; i < email.length; i++) {
    hash = ((hash * 31) + email.charCodeAt(i)) | 0;
  }

  const hue = ((hash % 360) + 360) % 360;

  return `
    --student-bg: hsl(${hue}, 76%, 92%);
    --student-border: hsl(${hue}, 55%, 76%);
    --student-text: hsl(${hue}, 65%, 23%);
  `;
}

function setScheduleStudentFilter(optionIndex, email) {
  const details = document.querySelectorAll(
    ".assigned-shifts-dropdown"
  )[optionIndex];

  const wasOpen = details ? details.open : false;

  state.scheduleStudentFilters[optionIndex] = email;
  render();

  const updatedDetails = document.querySelectorAll(
    ".assigned-shifts-dropdown"
  )[optionIndex];

  if (updatedDetails) {
    updatedDetails.open = wasOpen;
  }
}

function schedulePage() {
  const schedules = state.schedules || [];

  return `
    <div class="page-title">
      <div>
        <h1>Schedule</h1>
        <p class="muted">
          Generate and compare weekly employee schedules.
        </p>
      </div>
    </div>

    <div class="card schedule-generator">
      <h2>Generate Schedule</h2>

      <p class="muted">
        Create two schedule options using student availability
        and your saved scheduling constraints.
      </p>

      <div class="schedule-rule-summary">
        <div>
          <span class="stat-label">Combined maximum</span>
          <strong>${Number(state.rules.max_hours)} hours</strong>
        </div>

        <div>
          <span class="stat-label">Maximum per time slot</span>
          <strong>${Number(state.rules.max_per_slot)} employees</strong>
        </div>
      </div>

      <button
        class="primary action-button"
        id="generateScheduleButton"
        onclick="generateSchedule()"
      >
        Generate 2 Schedule Options
      </button>

      <p id="scheduleMessage" class="inline-message"></p>
    </div>

    ${
      schedules.length
        ? schedules.map((option, index) => {

          const assignments = option.assignments || [];

          const students = [
            ...new Set(assignments.map(a => a.email))
          ].sort((a, b) =>
            a.localeCompare(b, undefined, { numeric: true })
          );

          const selected =
            state.scheduleStudentFilters[index] || "";

          const filtered = assignments.filter(a =>
            !selected || a.email === selected
          );

          const sorted = [...filtered].sort((a, b) =>
            a.email.localeCompare(b.email, undefined, {
              numeric: true
            }) ||
            DAYS.findIndex(d => d.api === a.day) -
            DAYS.findIndex(d => d.api === b.day) ||
            Number(a.hour) - Number(b.hour)
          );

          return `
            <div class="card generated-schedule">

              <div class="generated-schedule-header">
                <div>
                  <h2>${escapeHtml(option.name)}</h2>
                  <p class="muted">
                    ${option.total_hours} total assigned hours
                  </p>
                </div>

                <span class="badge">Generated</span>
              </div>

              <div class="employee-calendar-wrapper">
                <table class="employee-calendar">
                  <thead>
                    <tr>
                      <th class="calendar-time-header">Time</th>
                      ${DAYS.map(day => `
                        <th>${day.label}</th>
                      `).join("")}
                    </tr>
                  </thead>

                  <tbody>
                    ${HOURS.map(hour => `
                      <tr>
                        <td class="calendar-time">
                          ${hourLabel(hour)}
                        </td>

                        ${DAYS.map(day => {
                          const assigned = filtered.filter(
                            item =>
                              item.day === day.api &&
                              Number(item.hour) === hour
                          );

                          return `
                            <td class="generated-calendar-cell">
                              ${
                                assigned.length
                                  ? assigned.map(item => `
                                    <div
                                      class="assigned-employee student-color"
                                      style="${studentColor(item.email)}"
                                    >
                                      ${escapeHtml(item.email)}
                                    </div>
                                  `).join("")
                                  : `<span class="availability-dash">—</span>`
                              }
                            </td>
                          `;
                        }).join("")}
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>

              <details class="assigned-shifts-dropdown">
                <summary>
                  <strong>Assigned Shifts</strong>
                  <span>${assignments.length} Assigned Hours</span>
                </summary>

                <div class="schedule-list-heading">
                  <label class="schedule-student-filter">
                    Filter Student

                    <select
                      onchange="setScheduleStudentFilter(${index}, this.value)"
                    >
                      <option value="">All Students</option>

                      ${students.map(email => `
                        <option
                          value="${escapeHtml(email)}"
                          ${selected === email ? "selected" : ""}
                        >
                          ${escapeHtml(email)}
                        </option>
                      `).join("")}
                    </select>
                  </label>
                </div>

                ${
                  sorted.length
                    ? `
                      <div class="shift-list">
                        ${sorted.map(assignment => `
                          <div
                            class="shift-row student-color"
                            style="${studentColor(assignment.email)}"
                          >
                            <strong>
                              ${escapeHtml(assignment.email)}
                            </strong>

                            <span>
                              ${escapeHtml(
                                DAYS.find(
                                  day => day.api === assignment.day
                                )?.label || assignment.day
                              )}
                            </span>

                            <span>
                              ${scheduleTimeLabel(Number(assignment.hour))}
                              –
                              ${scheduleTimeLabel(Number(assignment.hour) + 1)}
                            </span>

                            <span>1 hour</span>
                          </div>
                        `).join("")}
                      </div>
                    `
                    : `<p class="muted">No shifts assigned.</p>`
                }
              </details>

            </div>
          `;
        }).join("")
        : `
          <div class="card empty-state">
            <h3>No schedule generated yet</h3>
            <p class="muted">
              Click Generate 2 Schedule Options to create
              schedules from submitted student availability.
            </p>
          </div>
        `
    }
  `;
}

async function generateSchedule() {
  const button = document.getElementById(
    "generateScheduleButton"
  );

  const message = document.getElementById(
    "scheduleMessage"
  );

  if (!button || !message) {
    return;
  }

  button.disabled = true;
  button.textContent = "Generating...";
  message.textContent = "";

  try {
    const data = await api(
      "/api/generate-schedule",
      {
        method: "POST",
        body: {}
      }
    );

    state.schedules = data.options || [];
    state.scheduleStudentFilters = {};

    render();

  } catch (err) {
    message.textContent = err.message;
    message.className = "inline-message error";

    button.disabled = false;
    button.textContent = "Generate 2 Schedule Options";
  }
}

async function loadFacultyEmployees() {
  const data = await api("/api/employees");
  state.employees = data.employees || [];
}

async function loadFacultyDemand() {
  const data = await api("/api/demand");
  state.demand = data.demand || {};
}

async function loadFacultyRules() {
  state.rules = await api("/api/rules");
}

async function saveConstraints() {
  const maxHoursInput = document.getElementById("maxHours");
  const maxEmployeesInput = document.getElementById("maxEmployees");
  const message = document.getElementById("rulesMessage");
  const button = document.getElementById("saveConstraintsButton");

  if (!maxHoursInput || !maxEmployeesInput || !message) return;

  const maxHours = Number(maxHoursInput.value);
  const maxEmployees = Number(maxEmployeesInput.value);

  if (
    !Number.isInteger(maxHours) || maxHours < 1 ||
    !Number.isInteger(maxEmployees) || maxEmployees < 1
  ) {
    message.textContent = "Both constraints must be whole numbers of at least 1.";
    message.className = "inline-message error";
    return;
  }

  if (button) {
    button.disabled = true;
    button.textContent = "Saving...";
  }

  message.textContent = "";

  try {
    const saved = await api("/api/rules", {
      method: "PUT",
      body: { max_hours: maxHours, max_per_slot: maxEmployees }
    });

    state.rules = {
      max_hours: Number(saved.max_hours),
      max_per_slot: Number(saved.max_per_slot)
    };

    maxHoursInput.value = state.rules.max_hours;
    maxEmployeesInput.value = state.rules.max_per_slot;

    message.textContent = `Constraints saved: ${state.rules.max_hours} total hours, ${state.rules.max_per_slot} employees per time slot.`;
    message.className = "inline-message success";
  } catch (err) {
    message.textContent = `Could not save constraints: ${err.message}`;
    message.className = "inline-message error";
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "Save Constraints";
    }
  }
}

async function initSession() {
  try {
    const me = await api("/api/me");
    state.email = me.email;
    state.role = me.role;
    state.page = "app";
    state.nav = me.role === "faculty" ? "dashboard" : "availability";
    await loadCurrentPageData();
  } catch (err) {
    state.page = "login";
  }

  render();
}

window.addEventListener("DOMContentLoaded", initSession);
