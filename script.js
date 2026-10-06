// LostNoMore SQLite client layer
let reportsCache = [];
let usersCache = [];
let currentUser = null;

async function apiRequest(path, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (options.body && typeof options.body !== 'string') {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, opts);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

async function refreshDatabaseCache() {
  const data = await apiRequest('/api/bootstrap');
  reportsCache = data.reports || [];
  usersCache = data.users || [];
  currentUser = data.currentUser || null;
  return data;
}

async function migrateLegacyLocalStorage() {
  const legacyReports = window.localStorage.getItem('reports');
  const legacyUsers = window.localStorage.getItem('users');
  if (!legacyReports && !legacyUsers) return;
  try {
    await apiRequest('/api/migrate', {
      method: 'POST',
      body: {
        reports: legacyReports ? JSON.parse(legacyReports) : [],
        users: legacyUsers ? JSON.parse(legacyUsers) : []
      }
    });
    window.localStorage.removeItem('reports');
    window.localStorage.removeItem('users');
    window.localStorage.removeItem('lostNoMoreSeedVersion');
    window.localStorage.removeItem('currentUser');
    console.log('Legacy localStorage data migrated to SQLite.');
  } catch (error) {
    console.error('Legacy migration failed:', error);
  }
}

async function initializeSQLiteApp() {
  await migrateLegacyLocalStorage();
  await refreshDatabaseCache();
}

// Loading helper functions
function showLoading(button, originalText) {
  button.classList.add('loading');
  button.innerHTML = '<span class="loading-spinner"></span>Loading...';
  button.disabled = true;
}

function hideLoading(button, originalText) {
  button.classList.remove('loading');
  button.innerHTML = originalText;
  button.disabled = false;
}

// Validation functions
function validateName(name, errorId) {
  const error = document.getElementById(errorId);
  if (name.length < 2 || name.length > 50) {
    error.classList.add("show");
    return false;
  }
  error.classList.remove("show");
  return true;
}

function validateEmail(email, errorId) {
  const error = document.getElementById(errorId);
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    error.classList.add("show");
    return false;
  }
  error.classList.remove("show");
  return true;
}

function validatePassword(password, errorId) {
  const error = document.getElementById(errorId);
  if (password.length < 6) {
    error.classList.add("show");
    return false;
  }
  error.classList.remove("show");
  return true;
}

function validatePhone(phone, errorId) {
  const error = document.getElementById(errorId);
  const phoneRegex = /^[\d\s\-\+\(\)]+$/;
  if (!phoneRegex.test(phone) || phone.length < 10) {
    error.classList.add("show");
    return false;
  }
  error.classList.remove("show");
  return true;
}

function clearErrors() {
  document.querySelectorAll(".error-message").forEach(error => {
    error.classList.remove("show");
  });
}

// Search functionality
function searchReports(query) {
  const reports = reportsCache;
  const categoryFilter = document.getElementById('categoryFilter').value;
  const typeFilter = document.getElementById('typeFilter').value;
  const siteFilter = document.getElementById('siteFilter').value;
  const itemFilter = document.getElementById('itemFilter').value;
  const rewardFilter = document.getElementById('rewardFilter').value;
  const searchText = (query || '').toLowerCase();
  const filtered = reports.filter(report => {
    const textMatch = !query ||
      (report.name || '').toLowerCase().includes(searchText) ||
      (report.email || '').toLowerCase().includes(searchText) ||
      (report.description || '').toLowerCase().includes(searchText) ||
      (report.items || '').toLowerCase().includes(searchText) ||
      (report.site || '').toLowerCase().includes(searchText) ||
      (report.location || '').toLowerCase().includes(searchText);
    let categoryMatch = true;
    if (categoryFilter === 'type' && typeFilter) categoryMatch = (report.type || '').toLowerCase() === typeFilter;
    else if (categoryFilter === 'site' && siteFilter) categoryMatch = report.site === siteFilter;
    else if (categoryFilter === 'item' && itemFilter) categoryMatch = (report.items || '').split(',').map(x => x.trim()).includes(itemFilter);
    else if (categoryFilter === 'reward' && rewardFilter === 'yes') categoryMatch = !!(report.reward || '').trim();
    else if (categoryFilter === 'reward' && rewardFilter === 'no') categoryMatch = !(report.reward || '').trim();
    return textMatch && categoryMatch;
  });
  displayReports(filtered);
}

// Admin search functionality
function adminSearchReports(query) {
  const reports = reportsCache;
  const categoryFilter = document.getElementById('adminCategoryFilter').value;
  const typeFilter = document.getElementById('adminTypeFilter').value;
  const siteFilter = document.getElementById('adminSiteFilter').value;
  const itemFilter = document.getElementById('adminItemFilter').value;
  const rewardFilter = document.getElementById('adminRewardFilter').value;
  const searchText = (query || '').toLowerCase();
  const filtered = reports.filter(report => {
    const textMatch = !query ||
      (report.name || '').toLowerCase().includes(searchText) ||
      (report.email || '').toLowerCase().includes(searchText) ||
      (report.description || '').toLowerCase().includes(searchText) ||
      (report.items || '').toLowerCase().includes(searchText) ||
      (report.site || '').toLowerCase().includes(searchText) ||
      (report.location || '').toLowerCase().includes(searchText) ||
      (report.type || '').toLowerCase().includes(searchText);
    let categoryMatch = true;
    if (categoryFilter === 'type' && typeFilter) categoryMatch = (report.type || '').toLowerCase() === typeFilter;
    else if (categoryFilter === 'site' && siteFilter) categoryMatch = report.site === siteFilter;
    else if (categoryFilter === 'item' && itemFilter) categoryMatch = (report.items || '').split(',').map(x => x.trim()).includes(itemFilter);
    else if (categoryFilter === 'reward' && rewardFilter === 'yes') categoryMatch = !!(report.reward || '').trim();
    else if (categoryFilter === 'reward' && rewardFilter === 'no') categoryMatch = !(report.reward || '').trim();
    return textMatch && categoryMatch;
  });
  displayAdminReports(filtered);
}

// Display reports
function displayReports(reports) {
  const container = document.getElementById("reportsContainer");
  container.innerHTML = "";
  
  if (reports.length === 0) {
    container.innerHTML = "<p style='color: rgba(255, 255, 255, 0.7); text-align: center; padding: 20px;'>No reports found.</p>";
    return;
  }
  
  reports.forEach(report => {
    const div = document.createElement("div");
    div.className = `report-item ${report.type.toLowerCase()}`; // Add 'found' or 'lost' class
    
    // Check if user info should be hidden (admin marked as hidden)
    const isHidden = report.hiddenInfo || false;
    
    // Create image element if image data exists
    let imageHtml = '';
    if (report.imageData) {
      imageHtml = `<img src="${report.imageData}" alt="${report.items}" />`;
    }
    
    div.innerHTML = `
      ${imageHtml}
      <div class="report-content">
        <h4>${report.type} - ${report.items}</h4>
        <p><strong>Name:</strong> ${isHidden ? '[Hidden]' : report.name}</p>
        <p><strong>Email:</strong> ${isHidden ? '[Hidden]' : report.email}</p>
        <p><strong>Phone:</strong> ${isHidden ? '[Hidden]' : report.phone}</p>
        ${report.site ? `<p><strong>Site:</strong> ${report.site}</p>` : ""}
        ${report.location ? `<p><strong>Location:</strong> ${report.location}</p>` : ""}
        <p><strong>Description:</strong> ${report.description}</p>
        ${report.date ? `<p><strong>Date:</strong> ${report.date}</p>` : ""}
        ${report.reward ? `<p><strong>Reward:</strong> ${report.reward}</p>` : ""}
      </div>
    `;
    container.appendChild(div);
  });
}

// Show Lost Item form
function showLost() {
  const btn = event.target;
  const originalText = btn.innerHTML;
  showLoading(btn, originalText);
  
  setTimeout(() => {
    hideAll();
    document.getElementById("lost").classList.remove("hidden");
    hideLoading(btn, originalText);
  }, 800);
}

// Show Found Item form
function showFound() {
  const btn = event.target;
  const originalText = btn.innerHTML;
  showLoading(btn, originalText);
  
  setTimeout(() => {
    hideAll();
    document.getElementById("found").classList.remove("hidden");
    hideLoading(btn, originalText);
  }, 800);
}

// Show Reports
function showReports() {
  const btn = event ? event.target : null;
  const originalText = btn ? btn.innerHTML : 'View Reports';
  if (btn) showLoading(btn, originalText);
  setTimeout(async () => {
    try {
      hideAll();
      document.getElementById("reportsList").classList.remove("hidden");
      await refreshDatabaseCache();
      displayReports(reportsCache);
    } catch (error) {
      console.error(error);
      alert('Could not load reports from SQLite.');
    } finally {
      if (btn) hideLoading(btn, originalText);
    }
  }, btn ? 800 : 0);
}

// Hide Reports
function hideReports() {
  document.getElementById("reportsList").classList.add("hidden");
}

// Go back to dashboard (hide all forms)
function goBack() {
  const btn = event.target;
  const originalText = btn.innerHTML;
  
  if (btn && btn.tagName === 'BUTTON') {
    showLoading(btn, originalText);
    
    setTimeout(() => {
      hideAll();
      // Clear form data when going back
      document.querySelectorAll('form').forEach(form => {
        form.reset();
      });
      // Clear character counters
      document.querySelectorAll('.char-counter span').forEach(counter => {
        counter.textContent = '0';
      });
      // Clear selected items
      selectedItems = [];
      selectedFoundItems = [];
      selectedFoundSite = '';
      selectedLostSite = '';
      // Reset item button colors
      document.querySelectorAll('.item-buttons button').forEach(btn => {
        btn.classList.remove('selected');
      });
      // Reset site button colors
      document.querySelectorAll('.site-buttons button').forEach(btn => {
        btn.classList.remove('selected');
        btn.style.background = '#e8f4fd';
        btn.style.color = '#1a1a2e';
      });
      
      hideLoading(btn, originalText);
    }, 500);
  } else {
    // If no button clicked, execute immediately
    hideAll();
    // Clear form data when going back
    document.querySelectorAll('form').forEach(form => {
      form.reset();
    });
    // Clear character counters
    document.querySelectorAll('.char-counter span').forEach(counter => {
      counter.textContent = '0';
    });
    // Clear selected items
    selectedItems = [];
    selectedFoundItems = [];
    selectedFoundSite = '';
    selectedLostSite = '';
    // Reset item button colors
    document.querySelectorAll('.item-buttons button').forEach(btn => {
      btn.classList.remove('selected');
    });
    // Reset site button colors
    document.querySelectorAll('.site-buttons button').forEach(btn => {
      btn.classList.remove('selected');
      btn.classList.add('unselected');
      btn.style.color = '#1a1a2e';
    });
  }
}

// Hide all form sections
function hideAll() {
  document.querySelectorAll(".form-card").forEach(section => {
    section.classList.add("hidden");
  });
}

// Track selected sites
let selectedFoundSite = '';
let selectedLostSite = '';

// Select site for location
function selectSite(btn, type) {
  const site = btn.innerText;
  
  if (type === 'found') {
    // Clear previous selection
    document.querySelectorAll('#found .site-buttons button').forEach(button => {
      button.classList.remove('selected');
      button.style.background = '#e8f4fd';
      button.style.color = '#1a1a2e';
    });
    
    // Set new selection
    btn.classList.add('selected');
    btn.style.background = '#1a1a2e';
    btn.style.color = '#fff';
    selectedFoundSite = site;
  } else {
    // Clear previous selection
    document.querySelectorAll('#lost .site-buttons button').forEach(button => {
      button.classList.remove('selected');
      button.style.background = '#e8f4fd';
      button.style.color = '#1a1a2e';
    });
    
    // Set new selection
    btn.classList.add('selected');
    btn.style.background = '#1a1a2e';
    btn.style.color = '#fff';
    selectedLostSite = site;
  }
}

// Track selected items
let selectedItems = [];
let selectedFoundItems = [];

// Select Lost Item
function selectItem(btn) {
  toggleSelection(btn, selectedItems, "description", "lostOthersInput");
}

// Select Found Item
function selectFound(btn) {
  toggleSelection(btn, selectedFoundItems, "foundDescription", "foundOthersInput");
}

// Toggle item selection
function toggleSelection(btn, arr, descId, othersInputId) {
  const item = btn.innerText;
  
  // Handle Others category
  if (item === 'Others') {
    // Clear all other selections
    arr.length = 0;
    document.querySelectorAll('.item-buttons button').forEach(button => {
      if (button.innerText !== 'Others') {
        button.classList.remove('selected');
      }
    });
    
    // Show/hide others input
    const othersInput = document.getElementById(othersInputId);
    if (arr.includes('Others')) {
      // Deselect Others
      arr.splice(arr.indexOf('Others'), 1);
      btn.classList.remove('selected');
      othersInput.classList.remove('show');
    } else {
      // Select Others
      arr.push('Others');
      btn.classList.add('selected');
      othersInput.classList.add('show');
    }
  } else {
    // Handle regular items
    // Clear Others selection if any regular item is selected
    const othersBtn = Array.from(document.querySelectorAll('.item-buttons button')).find(b => b.innerText === 'Others');
    if (othersBtn) {
      const othersIndex = arr.indexOf('Others');
      if (othersIndex > -1) {
        arr.splice(othersIndex, 1);
        othersBtn.classList.remove('selected');
        document.getElementById(othersInputId).classList.remove('show');
      }
    }
    
    if (arr.includes(item)) {
      // Remove item from selection
      arr.splice(arr.indexOf(item), 1);
      btn.classList.remove('selected');
    } else {
      // Add item to selection
      arr.push(item);
      btn.classList.add('selected');
    }
  }

  // Update description field
  updateDescriptionField(arr, descId, othersInputId);
}

// Update description field based on selections
function updateDescriptionField(arr, descId, othersInputId) {
  let itemsText = '';
  
  if (arr.includes('Others')) {
    const othersInput = document.getElementById(othersInputId.replace('Input', 'Specify'));
    const othersValue = othersInput ? othersInput.value.trim() : '';
    if (othersValue) {
      itemsText = othersValue;
    }
  } else {
    itemsText = arr.join(", ");
  }
  
  document.getElementById(descId).value = itemsText;
  
  // Update character counter for description
  updateCharCounter(descId);
}

// Character counter functionality
function updateCharCounter(fieldId) {
  const field = document.getElementById(fieldId);
  const counterId = fieldId + "Count";
  const counter = document.getElementById(counterId);
  if (counter) {
    counter.textContent = field.value.length;
  }
}

// Save report to localStorage
async function saveReport(report) {
  try {
    await apiRequest('/api/reports', { method: 'POST', body: report });
    await refreshDatabaseCache();
    console.log('Report saved to SQLite:', report);
    return true;
  } catch (error) {
    console.error(error);
    alert('Could not save the report to SQLite: ' + error.message);
    return false;
  }
}

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const loginBtn = event.target;
  const originalText = loginBtn.innerHTML;
  showLoading(loginBtn, originalText);
  clearErrors();
  const isValid = validateEmail(email, "emailError") && validatePassword(password, "passwordError");
  if (!isValid) { hideLoading(loginBtn, originalText); return; }
  try {
    const data = await apiRequest('/api/login', { method: 'POST', body: { email, password } });
    currentUser = data.user;
    document.getElementById("userName").textContent = currentUser.name;
    document.getElementById("adminPanelBtn").classList.toggle("hidden", !currentUser.isAdmin);
    document.getElementById("loginPage").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");
    hideAll();
  } catch (error) {
    alert(error.message || 'Login failed.');
  } finally { hideLoading(loginBtn, originalText); }
}

function showCreateAccount() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    showLoading(btn, originalText);
    
    setTimeout(() => {
        document.getElementById("loginPage").classList.add("hidden");
        document.getElementById("createPage").classList.remove("hidden");
        clearErrors();
        hideLoading(btn, originalText);
    }, 600);
}

function showLogin() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    showLoading(btn, originalText);
    
    setTimeout(() => {
        document.getElementById("createPage").classList.add("hidden");
        document.getElementById("loginPage").classList.remove("hidden");
        clearErrors();
        hideLoading(btn, originalText);
    }, 600);
}

// Create account
async function createAccount() {
  const name = document.getElementById("createName").value.trim();
  const email = document.getElementById("createEmail").value.trim();
  const phone = document.getElementById("createPhone").value.trim();
  const password = document.getElementById("createPassword").value.trim();
  const confirmPassword = document.getElementById("confirmPassword").value.trim();
  const createBtn = event.target;
  const originalText = createBtn.innerHTML;
  showLoading(createBtn, originalText);
  clearErrors();
  let isValid = true;
  if (!validateName(name, "createNameError")) isValid = false;
  if (!validateEmail(email, "createEmailError")) isValid = false;
  if (!validatePhone(phone, "createPhoneError")) isValid = false;
  if (!validatePassword(password, "createPasswordError")) isValid = false;
  if (password !== confirmPassword) {
    document.getElementById("confirmPasswordError").classList.add("show");
    isValid = false;
  }
  if (!isValid) { hideLoading(createBtn, originalText); return; }
  try {
    await apiRequest('/api/users', { method: 'POST', body: { name, email, phone, password } });
    await refreshDatabaseCache();
    alert('Account created successfully! You can now login.');
    showLogin();
  } catch (error) {
    alert(error.message || 'Could not create account.');
  } finally { hideLoading(createBtn, originalText); }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', async function() {
  try { await initializeSQLiteApp(); } catch (error) { console.error(error); alert('Could not connect to the SQLite database. Make sure you started run.py.'); return; }
  // Add Enter key support for login form
  const passwordField = document.getElementById('password');
  const emailField = document.getElementById('email');
  
  if (passwordField) {
    passwordField.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        // Find and click the login button
        const loginBtn = document.querySelector('#loginForm button[onclick="login()"]');
        if (loginBtn) {
          loginBtn.click();
        }
      }
    });
  }
  
  if (emailField) {
    emailField.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        // Move to password field
        passwordField.focus();
      }
    });
  }
  
  // Character counters for all inputs
  const inputs = [
    'email', 'password', 'createName', 'createEmail', 'createPhone', 
    'createPassword', 'confirmPassword', 'foundName', 'foundEmail', 'foundPhone',
    'foundLocation', 'foundDescription', 'foundOthersSpecify',
    'lostName', 'lostEmail', 'lostPhone', 'lostLocation', 'description', 'lostOthersSpecify', 'lostReward'
  ];
  
  inputs.forEach(id => {
    const element = document.getElementById(id);
    if (element) {
      element.addEventListener('input', () => updateCharCounter(id));
      element.addEventListener('blur', () => {
        if (id.includes('name')) validateName(element.value, id + 'Error');
        if (id.includes('email')) validateEmail(element.value, id + 'Error');
        if (id.includes('phone')) validatePhone(element.value, id + 'Error');
        if (id.includes('Password')) validatePassword(element.value, id + 'Error');
      });
    }
  });
  
  // Category filter event listeners
  const categoryFilter = document.getElementById('categoryFilter');
  const adminCategoryFilter = document.getElementById('adminCategoryFilter');
  
  if (categoryFilter) {
    categoryFilter.addEventListener('change', function() {
      const typeFilter = document.getElementById('typeFilter');
      const siteFilter = document.getElementById('siteFilter');
      const itemFilter = document.getElementById('itemFilter');
      const rewardFilter = document.getElementById('rewardFilter');
      
      // Hide all sub-filters first
      if (typeFilter) typeFilter.style.display = 'none';
      if (siteFilter) siteFilter.style.display = 'none';
      if (itemFilter) itemFilter.style.display = 'none';
      if (rewardFilter) rewardFilter.style.display = 'none';
      
      // Show relevant sub-filter
      if (this.value === 'type' && typeFilter) {
        typeFilter.style.display = 'block';
      } else if (this.value === 'site' && siteFilter) {
        siteFilter.style.display = 'block';
      } else if (this.value === 'item' && itemFilter) {
        itemFilter.style.display = 'block';
      } else if (this.value === 'reward' && rewardFilter) {
        rewardFilter.style.display = 'block';
      }
      
      // Trigger search
      searchReports(document.getElementById('searchInput').value);
    });
  }
  
  if (adminCategoryFilter) {
    adminCategoryFilter.addEventListener('change', function() {
      const adminTypeFilter = document.getElementById('adminTypeFilter');
      const adminSiteFilter = document.getElementById('adminSiteFilter');
      const adminItemFilter = document.getElementById('adminItemFilter');
      const adminRewardFilter = document.getElementById('adminRewardFilter');
      
      // Hide all sub-filters first
      if (adminTypeFilter) adminTypeFilter.style.display = 'none';
      if (adminSiteFilter) adminSiteFilter.style.display = 'none';
      if (adminItemFilter) adminItemFilter.style.display = 'none';
      if (adminRewardFilter) adminRewardFilter.style.display = 'none';
      
      // Show relevant sub-filter
      if (this.value === 'type' && adminTypeFilter) {
        adminTypeFilter.style.display = 'block';
      } else if (this.value === 'site' && adminSiteFilter) {
        adminSiteFilter.style.display = 'block';
      } else if (this.value === 'item' && adminItemFilter) {
        adminItemFilter.style.display = 'block';
      } else if (this.value === 'reward' && adminRewardFilter) {
        adminRewardFilter.style.display = 'block';
      }
      
      // Trigger search
      adminSearchReports(document.getElementById('adminSearchInput').value);
    });
  }
  
  // Form submissions
  document.getElementById('foundForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.click();
    }
  });
  
  document.getElementById('lostForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.click();
    }
  });
  
  // Install the requested 150-report demo dataset before the app reads reports.
  seedDemoReports();

  // Check if user is already logged in
  if (currentUser) {
    document.getElementById("userName").textContent = currentUser.name;
    if (currentUser.isAdmin) {
      document.getElementById("adminPanelBtn").classList.remove("hidden");
    } else {
      document.getElementById("adminPanelBtn").classList.add("hidden");
    }
    document.getElementById("loginPage").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");
    hideAll(); // Hide all forms and reports to show clean dashboard first
    document.getElementById("reportsList").classList.add("hidden"); // Ensure reports list is hidden
  }
  
  // Don't auto-load reports - let users choose from dashboard
});


// ============================================================
// ICCT Colleges - Main Campus only
// 150 reports total: 80 Lost + 70 Found
// Filipino names and Philippine contact details
// ============================================================
async function seedDemoReports() {
  // Demo data is seeded by the SQLite backend.
  return;
}

// Toggle Help Modal
function toggleHelpModal() {
  const modal = document.getElementById('helpModal');
  modal.classList.toggle('show');
}

// Switch Campus Information
function switchCampus(campus) {
  // Hide all campus info
  document.querySelectorAll('.campus-info').forEach(info => {
    info.classList.remove('active');
  });
  
  // Remove active class from all buttons
  document.querySelectorAll('.campus-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected campus info
  document.getElementById(campus + '-campus').classList.add('active');
  
  // Add active class to clicked button
  event.target.classList.add('active');
}

// Make help modal draggable
let isDragging = false;
let currentX;
let currentY;
let initialX;
let initialY;
let xOffset = 0;
let yOffset = 0;

const helpModal = document.getElementById('helpModal');
const helpHeader = document.querySelector('.help-header');

function dragStart(e) {
  if (e.type === "touchstart") {
    initialX = e.touches[0].clientX - xOffset;
    initialY = e.touches[0].clientY - yOffset;
  } else {
    initialX = e.clientX - xOffset;
    initialY = e.clientY - yOffset;
  }

  if (e.target === helpHeader || helpHeader.contains(e.target)) {
    isDragging = true;
  }
}

function dragEnd(e) {
  initialX = currentX;
  initialY = currentY;
  isDragging = false;
}

function drag(e) {
  if (isDragging) {
    e.preventDefault();
    
    if (e.type === "touchmove") {
      currentX = e.touches[0].clientX - initialX;
      currentY = e.touches[0].clientY - initialY;
    } else {
      currentX = e.clientX - initialX;
      currentY = e.clientY - initialY;
    }

    xOffset = currentX;
    yOffset = currentY;

    helpModal.style.transform = `translate(${currentX}px, ${currentY}px)`;
  }
}

// Add event listeners for dragging - DISABLED
// helpHeader.addEventListener('mousedown', dragStart);
// document.addEventListener('mousemove', drag);
// document.addEventListener('mouseup', dragEnd);

// Touch events for mobile - DISABLED
// helpHeader.addEventListener('touchstart', dragStart);
// document.addEventListener('touchmove', drag);
// document.addEventListener('touchend', dragEnd);

// Show Admin Panel
function showAdminPanel() {
  const btn = event.target;
  const originalText = btn.innerHTML;
  
  // Show loading state
  showLoading(btn, originalText);
  
  setTimeout(() => {
    // Check if current user is admin
    if (!currentUser || !currentUser.isAdmin) {
      hideLoading(btn, originalText);
      alert('Access denied! Only admin users can access this panel.');
      return;
    }
    
    hideAll();
    document.getElementById("adminPanel").classList.remove("hidden");
    showAllReports();
    hideLoading(btn, originalText);
  }, 600);
}

// Show all reports for admin
async function showAllReports() {
  try {
    await refreshDatabaseCache();
    displayAdminReports(reportsCache);
  } catch (error) {
    console.error(error);
    alert('Could not load reports from SQLite.');
  }
}

// Display admin reports with controls
function displayAdminReports(reports) {
  const container = document.getElementById("adminReportsContainer");
  container.innerHTML = "";
  if (!reports.length) {
    container.innerHTML = "<p style='color: rgba(255, 255, 255, 0.7); text-align: center; padding: 20px;'>No reports found.</p>";
    return;
  }
  reports.forEach(report => {
    const div = document.createElement("div");
    div.className = `admin-report-item ${report.type.toLowerCase()}`;
    div.id = `report-${report.id}`;
    const isHidden = !!report.hiddenInfo;
    const imageHtml = report.imageData ? `<img src="${report.imageData}" alt="${report.items || 'report image'}" />` : '';
    div.innerHTML = `
      ${imageHtml}
      <div class="report-content">
        <h4>${report.type} - ${report.items}</h4>
        <p><strong>Name:</strong> ${isHidden ? '[Hidden]' : report.name}</p>
        <p><strong>Email:</strong> ${isHidden ? '[Hidden]' : report.email}</p>
        <p><strong>Phone:</strong> ${isHidden ? '[Hidden]' : report.phone}</p>
        ${report.site ? `<p><strong>Site:</strong> ${report.site}</p>` : ""}
        ${report.location ? `<p><strong>Location:</strong> ${report.location}</p>` : ""}
        <p><strong>Description:</strong> ${report.description}</p>
        ${report.date ? `<p><strong>Date:</strong> ${report.date}</p>` : ""}
        ${report.reward ? `<p><strong>Reward:</strong> ${report.reward}</p>` : ""}
      </div>
      <div class="report-actions">
        <button class="toggle-info-btn" onclick="toggleUserInfo('${report.id}')">${isHidden ? 'Show Info' : 'Hide Info'}</button>
        <button class="edit-btn" onclick="openEditModal('${report.id}')">Edit</button>
        <button class="delete-btn" onclick="deleteReport('${report.id}')">Delete</button>
      </div>`;
    div.classList.add(report.imageData ? 'has-image' : 'no-image');
    container.appendChild(div);
  });
}

// Toggle user information visibility
async function toggleUserInfo(reportId) {
  try {
    await apiRequest(`/api/reports/${encodeURIComponent(reportId)}/toggle-hidden`, { method: 'POST', body: {} });
    await refreshDatabaseCache();
    displayAdminReports(reportsCache);
    displayReports(reportsCache);
  } catch (error) { alert(error.message || 'Could not update report privacy.'); }
}

// Open Edit Modal
function openEditModal(reportId) {
  const report = reportsCache.find(r => r.id === reportId);
  if (!report) return alert('Report not found.');
  document.getElementById('editReportIndex').value = report.id;
  document.getElementById('editType').value = report.type;
  document.getElementById('editName').value = report.name;
  document.getElementById('editEmail').value = report.email;
  document.getElementById('editPhone').value = report.phone;
  document.getElementById('editItems').value = report.items;
  document.getElementById('editDescription').value = report.description;
  document.getElementById('editSite').value = report.site || '';
  document.getElementById('editLocation').value = report.location || '';
  document.getElementById('editDate').value = report.date || '';
  document.getElementById('editReward').value = report.reward || '';
  document.getElementById('editDateGroup').style.display = report.type === 'Lost' ? 'block' : 'none';
  document.getElementById('editRewardGroup').style.display = report.type === 'Lost' ? 'block' : 'none';
  const currentImage = document.getElementById('currentImage');
  if (report.imageData) { currentImage.src = report.imageData; currentImage.style.display = 'block'; }
  else currentImage.style.display = 'none';
  document.getElementById('editModal').style.display = 'block';
}

// Close Edit Modal
function closeEditModal() {
  document.getElementById('editModal').style.display = 'none';
}

// Remove Image
function removeImage() {
  const currentImage = document.getElementById('currentImage');
  currentImage.style.display = 'none';
  // Note: Image will be removed when saved
}

// Save Edited Report
async function saveEditedReport(event) {
  event.preventDefault();
  if (!confirm('Are you sure you want to save these changes to this report?')) return;
  const adminPassword = prompt('Please enter admin password to confirm this change:');
  if (!adminPassword) return;
  try {
    await apiRequest('/api/admin/verify', { method: 'POST', body: { password: adminPassword } });
    const reportId = document.getElementById('editReportIndex').value;
    const report = reportsCache.find(r => r.id === reportId);
    if (!report) return alert('Report not found.');
    report.type = document.getElementById('editType').value;
    report.name = document.getElementById('editName').value.trim();
    report.email = document.getElementById('editEmail').value.trim();
    report.phone = document.getElementById('editPhone').value.trim();
    report.items = document.getElementById('editItems').value.trim();
    report.description = document.getElementById('editDescription').value.trim();
    report.site = document.getElementById('editSite').value;
    report.location = document.getElementById('editLocation').value.trim();
    report.date = document.getElementById('editDate').value;
    report.reward = document.getElementById('editReward').value.trim();
    if (!report.type || !report.name || !report.email || !report.phone || !report.items || !report.description)
      return alert('Please fill in all required fields: Type, Name, Email, Phone, Items, and Description are required.');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(report.email)) return alert('Please enter a valid email address.');
    if (report.phone.length < 10) return alert('Please enter a valid phone number (at least 10 digits).');
    if (document.getElementById('currentImage').style.display === 'none') report.imageData = null;
    await apiRequest(`/api/reports/${encodeURIComponent(reportId)}`, { method: 'PUT', body: report });
    await refreshDatabaseCache();
    displayAdminReports(reportsCache);
    displayReports(reportsCache);
    closeEditModal();
    alert('Report updated successfully!');
  } catch (error) { alert(error.message || 'Could not update report.'); }
}

// Delete Report
async function deleteReport(reportId) {
  if (!confirm('Are you sure you want to delete this report? This action cannot be undone.')) return;
  const adminPassword = prompt('Please enter admin password to confirm this deletion:');
  if (!adminPassword) return;
  try {
    await apiRequest('/api/admin/verify', { method: 'POST', body: { password: adminPassword } });
    await apiRequest(`/api/reports/${encodeURIComponent(reportId)}`, { method: 'DELETE' });
    await refreshDatabaseCache();
    displayAdminReports(reportsCache);
    alert('Report deleted successfully!');
  } catch (error) { alert(error.message || 'Report was not deleted.'); }
}

// Admin Search Function
function adminSearchReports(query) {
  const reports = reportsCache;
  const categoryFilter = document.getElementById('adminCategoryFilter').value;
  const typeFilter = document.getElementById('adminTypeFilter').value;
  const siteFilter = document.getElementById('adminSiteFilter').value;
  const itemFilter = document.getElementById('adminItemFilter').value;
  const rewardFilter = document.getElementById('adminRewardFilter').value;
  const searchText = (query || '').toLowerCase();
  const filtered = reports.filter(report => {
    const textMatch = !query ||
      (report.name || '').toLowerCase().includes(searchText) ||
      (report.email || '').toLowerCase().includes(searchText) ||
      (report.description || '').toLowerCase().includes(searchText) ||
      (report.items || '').toLowerCase().includes(searchText) ||
      (report.site || '').toLowerCase().includes(searchText) ||
      (report.location || '').toLowerCase().includes(searchText) ||
      (report.type || '').toLowerCase().includes(searchText);
    let categoryMatch = true;
    if (categoryFilter === 'type' && typeFilter) categoryMatch = (report.type || '').toLowerCase() === typeFilter;
    else if (categoryFilter === 'site' && siteFilter) categoryMatch = report.site === siteFilter;
    else if (categoryFilter === 'item' && itemFilter) categoryMatch = (report.items || '').split(',').map(x => x.trim()).includes(itemFilter);
    else if (categoryFilter === 'reward' && rewardFilter === 'yes') categoryMatch = !!(report.reward || '').trim();
    else if (categoryFilter === 'reward' && rewardFilter === 'no') categoryMatch = !(report.reward || '').trim();
    return textMatch && categoryMatch;
  });
  displayAdminReports(filtered);
}

// Export Reports
function exportReports() {
  const dataStr = JSON.stringify(reportsCache, null, 2);
  const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
  const exportFileDefaultName = `lostnomore_reports_${new Date().toISOString().split('T')[0]}.json`;
  const linkElement = document.createElement('a');
  linkElement.setAttribute('href', dataUri);
  linkElement.setAttribute('download', exportFileDefaultName);
  linkElement.click();
  alert('Reports exported successfully!');
}

// Show Delete User Dialog
async function showDeleteUserDialog() {
  try {
    await refreshDatabaseCache();
    const users = usersCache.filter(u => !u.isAdmin);
    if (!users.length) return alert('No user accounts found to delete.');
    let userList = '📋 Select a user to delete:\n\n';
    users.forEach((user, index) => { userList += `${index + 1}. ${user.name} (${user.email})\n`; });
    const selection = prompt(userList + '\nEnter the number of the user to delete (or 0 to cancel):');
    if (selection === null || selection === '0') return;
    const userIndex = parseInt(selection) - 1;
    if (isNaN(userIndex) || userIndex < 0 || userIndex >= users.length) return alert('Invalid selection. Please try again.');
    const selectedUser = users[userIndex];
    if (confirm(`Are you sure you want to delete ${selectedUser.name} (${selectedUser.email})?\n\nThis will also delete all their reports and cannot be undone.`))
      await deleteUserAccount(selectedUser.email, false);
  } catch (error) { alert(error.message || 'Could not load user accounts.'); }
}

// Delete User Account
async function deleteUserAccount(email, askConfirmation = true) {
  if (askConfirmation && !confirm(`Are you sure you want to delete the account for ${email}? This action cannot be undone.`)) return;
  try {
    await apiRequest(`/api/users?email=${encodeURIComponent(email)}`, { method: 'DELETE' });
    await refreshDatabaseCache();
    alert(`Account for ${email} and all associated reports have been deleted.`);
    showAllReports();
  } catch (error) { alert(error.message || 'User was not deleted.'); }
}

// View User Accounts
async function viewUserAccounts() {
  try {
    await refreshDatabaseCache();
    const users = usersCache.filter(u => !u.isAdmin);
    if (!users.length) return alert('No user accounts found.');
    let userList = '📋 Registered User Accounts:\n\n';
    users.forEach((user, index) => {
      userList += `${index + 1}. ${user.name} (${user.email})\n`;
      userList += `   Phone: ${user.phone || 'N/A'}\n`;
      userList += `   Created: ${new Date(user.createdAt).toLocaleDateString()}\n\n`;
    });
    alert(userList);
  } catch (error) { alert(error.message || 'Could not load user accounts.'); }
}

// Logout function
async function logout() {
  const btn = event.target;
  const originalText = btn.innerHTML;
  showLoading(btn, originalText);
  try {
    await apiRequest('/api/logout', { method: 'POST', body: {} });
    currentUser = null;
    document.getElementById("dashboard").classList.add("hidden");
    document.getElementById("loginPage").classList.remove("hidden");
    document.getElementById("loginForm").reset();
    document.querySelectorAll('.char-counter span').forEach(counter => counter.textContent = '0');
    clearErrors();
    alert('You have been logged out successfully!');
  } catch (error) { alert(error.message || 'Logout failed.'); }
  finally { hideLoading(btn, originalText); }
}

// Submit Found Report
function submitFoundReport() {
  const submitBtn = event ? event.target : document.querySelector('#foundForm .submit-btn');
  const originalText = submitBtn.innerHTML;
  
  // Show loading state
  showLoading(submitBtn, originalText);
  
  setTimeout(() => {
    clearErrors();
    
    const name = document.getElementById('foundName').value.trim();
    const email = document.getElementById('foundEmail').value.trim();
    const phone = document.getElementById('foundPhone').value.trim();
    const location = document.getElementById('foundLocation').value.trim();
    const description = document.getElementById('foundDescription').value.trim();
    const fileInput = document.getElementById('foundFile');
    
    let isValid = true;
    if (!validateName(name, 'foundNameError')) isValid = false;
    if (!validateEmail(email, 'foundEmailError')) isValid = false;
    if (!validatePhone(phone, 'foundPhoneError')) isValid = false;
    if (!selectedFoundSite) {
      hideLoading(submitBtn, originalText);
      alert('Please select where the item was found');
      isValid = false;
    }
    if (location.length < 3) {
      document.getElementById('foundLocationError').classList.add('show');
      isValid = false;
    }
    
    if (!isValid) {
      hideLoading(submitBtn, originalText);
      return;
    }
    
    // Image upload
    let imageData = null;
    if (fileInput.files && fileInput.files[0]) {
      const reader = new FileReader();
      reader.onload = function(e) {
        imageData = e.target.result;
        saveFoundReportWithData(imageData, submitBtn, originalText);
      };
      reader.readAsDataURL(fileInput.files[0]);
    } else {
      saveFoundReportWithData(null, submitBtn, originalText);
    }
  }, 800);
}

async function saveFoundReportWithData(imageData, submitBtn, originalText) {
  const name = document.getElementById('foundName').value.trim();
  const email = document.getElementById('foundEmail').value.trim();
  const phone = document.getElementById('foundPhone').value.trim();
  const location = document.getElementById('foundLocation').value.trim();
  const description = document.getElementById('foundDescription').value.trim();
  let itemName = '';
  if (selectedFoundItems.includes('Others')) {
    const othersValue = document.getElementById('foundOthersSpecify').value.trim();
    if (!othersValue) { hideLoading(submitBtn, originalText); alert('Please specify the item when selecting "Others"'); return; }
    itemName = othersValue;
  } else if (selectedFoundItems.length > 0) itemName = selectedFoundItems.join(', ');
  else { hideLoading(submitBtn, originalText); alert('Please select at least one item'); return; }

  const report = {
    type: 'Found', name, email, phone, site: selectedFoundSite, location,
    items: itemName, description, imageData, timestamp: new Date().toISOString()
  };
  if (await saveReport(report)) {
    hideLoading(submitBtn, originalText);
    alert('Found report submitted successfully! Location: ' + selectedFoundSite + ' - ' + location);
    goBack();
    showReports();
  } else hideLoading(submitBtn, originalText);
}

// Submit lost report
function submitLostReport() {
  const submitBtn = event ? event.target : document.querySelector('#lostForm .submit-btn');
  const originalText = submitBtn.innerHTML;
  
  // Show loading state
  showLoading(submitBtn, originalText);
  
  setTimeout(() => {
    clearErrors();
    
    const name = document.getElementById('lostName').value.trim();
    const email = document.getElementById('lostEmail').value.trim();
    const phone = document.getElementById('lostPhone').value.trim();
    const location = document.getElementById('lostLocation').value.trim();
    const date = document.getElementById('lostDate').value;
    const description = document.getElementById('description').value.trim();
    const reward = document.getElementById('lostReward').value.trim();
    const fileInput = document.querySelectorAll('#lostForm input[type="file"]')[0]; // Reference the file input

    let isValid = true;
    if (!validateName(name, 'lostNameError')) isValid = false;
    if (!validateEmail(email, 'lostEmailError')) isValid = false;
    if (!validatePhone(phone, 'lostPhoneError')) isValid = false;
    if (!selectedLostSite) {
      hideLoading(submitBtn, originalText);
      alert('Please select where you lost the item');
      isValid = false;
    }
    if (location.length < 3) {
      document.getElementById('lostLocationError').classList.add('show');
      isValid = false;
    }
    if (!date) {
      hideLoading(submitBtn, originalText);
      alert('Please select date lost');
      isValid = false;
    }
    
    // Date format validation for lost report
    if (date) {
      const dateParts = date.split('/');
      if (dateParts.length === 3 && dateParts[2]) {
        const year = parseInt(dateParts[2]);
        // Check if year is exactly 4 digits
        if (!/^\d{4}$/.test(dateParts[2])) {
          hideLoading(submitBtn, originalText);
          alert('Year must be exactly 4 digits (yyyy format).');
          isValid = false;
        }
        // Check if year is within reasonable range (1900-2100)
        if (year < 1900 || year > 2100) {
          hideLoading(submitBtn, originalText);
          alert('Year must be between 1900 and 2100.');
          isValid = false;
        }
      }
    }
    
    if (!isValid) {
      hideLoading(submitBtn, originalText);
      return;
    }

    // Handle Image Upload
    if (fileInput.files && fileInput.files[0]) {
      const reader = new FileReader();
      reader.onload = function(e) {
        saveLostReportWithData(e.target.result, submitBtn, originalText);
      };
      reader.readAsDataURL(fileInput.files[0]);
    } else {
      saveLostReportWithData(null, submitBtn, originalText);
    }
  }, 800);
}

// New helper function to save the data
async function saveLostReportWithData(imageData, submitBtn, originalText) {
  const name = document.getElementById('lostName').value.trim();
  const email = document.getElementById('lostEmail').value.trim();
  const phone = document.getElementById('lostPhone').value.trim();
  const location = document.getElementById('lostLocation').value.trim();
  const date = document.getElementById('lostDate').value;
  const description = document.getElementById('description').value.trim();
  const reward = document.getElementById('lostReward').value.trim();
  let itemName = selectedItems.join(', ');
  if (selectedItems.includes('Others')) itemName = document.getElementById('lostOthersSpecify').value.trim();

  const report = {
    type: 'Lost', name, email, phone, site: selectedLostSite, location, date,
    items: itemName, description, reward: reward || null, imageData,
    timestamp: new Date().toISOString()
  };
  if (await saveReport(report)) {
    hideLoading(submitBtn, originalText);
    alert('Lost report submitted successfully!');
    goBack();
    showReports();
  } else hideLoading(submitBtn, originalText);
}