// Kiyim AI Mobile Client Script
let selectedGarmentUrl = '/static/garments/garment_1.jpg';
let selectedSize = 'M';
let userImageBlob = null;
let garmentImageBlob = null;
let cameraStream = null;

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  loadHistory();
});

// Tab almashtirish (Bottom Navigation)
function switchTab(tabName) {
  document.querySelectorAll('.tab-page').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('text-indigo-400');
    btn.classList.add('text-zinc-500');
  });

  const activeTab = document.getElementById(`tab-${tabName}`);
  const activeNav = document.getElementById(`nav-${tabName}`);

  if (activeTab) activeTab.classList.remove('hidden');
  if (activeNav) {
    activeNav.classList.remove('text-zinc-500');
    activeNav.classList.add('text-indigo-400');
  }

  // Agar kameradan chiqilsa, streamni to'xtatish
  if (tabName !== 'camera' && cameraStream) {
    stopCamera();
  }

  if (tabName === 'history') {
    loadHistory();
  }

  if (window.lucide) lucide.createIcons();
}

// O'lcham tanlash
function chooseSize(size, btnElement) {
  selectedSize = size;
  document.querySelectorAll('.size-btn').forEach(btn => {
    btn.className = 'size-btn py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-400 hover:border-zinc-600 transition';
  });
  btnElement.className = 'size-btn py-2.5 rounded-xl bg-indigo-600 border border-indigo-400 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 transition';
  document.getElementById('current-size-display').innerText = `${size}`;
}

// Foydalanuvchi rasmini tanlash
function handleUserFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  userImageBlob = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('user-img-element').src = e.target.result;
  };
  reader.readAsDataURL(file);
}

// Kiyim rasmini tanlash
function handleGarmentFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  garmentImageBlob = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('garment-img-element').src = e.target.result;
    selectedGarmentUrl = null; // Maxsus yuklangan fayldan foydalanish
  };
  reader.readAsDataURL(file);
}

// Katalogdan kiyim tanlash
function selectGarment(imageUrl, title, cardElement) {
  selectedGarmentUrl = imageUrl;
  garmentImageBlob = null;
  document.getElementById('garment-img-element').src = imageUrl;

  document.querySelectorAll('.garment-card').forEach(c => {
    c.classList.remove('ring-2', 'ring-indigo-500', 'border-transparent');
    c.classList.add('border-zinc-800');
  });
  if (cardElement) {
    cardElement.classList.add('ring-2', 'ring-indigo-500', 'border-transparent');
    cardElement.classList.remove('border-zinc-800');
  }
}

function useInStudio(imageUrl, title) {
  selectGarment(imageUrl, title, null);
  switchTab('studio');
}

// Yangi kiyim yuklash
async function uploadNewGarment(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('image', file);
  formData.append('title', 'Yangi Kiyim ' + new Date().toLocaleTimeString());
  formData.append('category', 'upper_body');

  try {
    const res = await fetch('/api/garments', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      alert("Yangi kiyim katalogga muvaffaqiyatli qo'shildi!");
      window.location.reload();
    }
  } catch (err) {
    alert("Kiyim yuklashda xatolik yuz berdi");
  }
}

// Jonli Kamera funksiyalari
async function openLiveCamera() {
  switchTab('camera');
  const video = document.getElementById('live-video');
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 720 }, height: { ideal: 960 } },
      audio: false
    });
    video.srcObject = cameraStream;
  } catch (err) {
    alert("Kameraga ulanib bo'lmadi: " + err.message);
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
}

function captureFromCamera() {
  const video = document.getElementById('live-video');
  const canvas = document.getElementById('live-canvas');
  if (!video.videoWidth) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    userImageBlob = blob;
    document.getElementById('user-img-element').src = URL.createObjectURL(blob);
    stopCamera();
    switchTab('studio');
  }, 'image/jpeg', 0.9);
}

let lastOriginalImageUrl = '';
let lastResultImageUrl = '';

function showOriginalImage() {
  if (lastOriginalImageUrl) {
    document.getElementById('result-img-element').src = lastOriginalImageUrl;
    document.getElementById('toggle-before-after-btn').classList.add('bg-zinc-700');
  }
}

function showResultImage() {
  if (lastResultImageUrl) {
    document.getElementById('result-img-element').src = lastResultImageUrl;
    document.getElementById('toggle-before-after-btn').classList.remove('bg-zinc-700');
  }
}

// Asosiy Try-On jarayoni
async function executeTryOn() {
  const loading = document.getElementById('tryon-loading');
  const submitBtn = document.getElementById('tryon-submit-btn');
  const resultBox = document.getElementById('tryon-result-box');

  loading.classList.remove('hidden');
  resultBox.classList.add('hidden');
  submitBtn.disabled = true;

  try {
    const formData = new FormData();
    if (userImageBlob) {
      formData.append('user_image', userImageBlob, 'user.jpg');
    } else {
      formData.append('user_image_url', '/static/uploads/sample_user.jpg');
    }

    if (garmentImageBlob) {
      formData.append('garment_image', garmentImageBlob, 'garment.jpg');
    } else if (selectedGarmentUrl) {
      formData.append('garment_url', selectedGarmentUrl);
    }

    formData.append('selected_size', selectedSize);

    const res = await fetch('/api/tryon', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || "Try-On ishlovida xatolik");
    }

    // Natijalarni ko'rsatish
    lastResultImageUrl = data.result_image_url + '?t=' + Date.now();
    lastOriginalImageUrl = data.user_image_url;

    document.getElementById('result-img-element').src = lastResultImageUrl;
    document.getElementById('fit-percent').innerText = `${data.match_percentage}%`;
    document.getElementById('fit-bar').style.width = `${data.match_percentage}%`;
    document.getElementById('fit-advice-text').innerText = data.fit_advice;
    document.getElementById('fit-rec-size').innerText = `Tavsiya etilgan o'lcham: ${data.recommended_size}`;

    // Fit Badge va Vizual effekti
    const badge = document.getElementById('fit-badge');
    const visualTag = document.getElementById('fit-visual-effect');

    if (data.fit_status === 'perfect') {
      badge.innerText = 'Ideal Moslik';
      badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
      if (visualTag) visualTag.innerText = '✨ Anatomik qulay siluet';
    } else if (data.fit_status === 'tight') {
      badge.innerText = 'Biroz Tor';
      badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30';
      if (visualTag) visualTag.innerText = '⚠️ Siqilgan mato & taranglik burmalari';
    } else {
      badge.innerText = 'Katta / Oversized';
      badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30';
      if (visualTag) visualTag.innerText = '👕 Drop-shoulder & erkin osilgan mato';
    }

    resultBox.classList.remove('hidden');
    resultBox.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    loading.classList.add('hidden');
    submitBtn.disabled = false;
  }
}

// Tarixni yuklash
async function loadHistory() {
  const container = document.getElementById('history-list');
  const countEl = document.getElementById('history-count');
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    countEl.innerText = `${data.length} ta kiyib ko'rish yozuvi`;

    if (!data || data.length === 0) {
      container.innerHTML = `
        <div class="text-center py-16 text-zinc-500 text-xs">
          <i data-lucide="shirt" class="w-10 h-10 mx-auto mb-2 text-zinc-700"></i>
          Hali hech qanday kiyim kiyib ko'rilmagan
        </div>
      `;
      if (window.lucide) lucide.createIcons();
      return;
    }

    container.innerHTML = data.map(item => `
      <div class="bg-zinc-900 border border-zinc-800 rounded-3xl p-3 flex items-center space-x-3 relative group">
        <div class="w-20 h-24 rounded-2xl bg-black overflow-hidden flex-shrink-0">
          <img src="${item.result_image_url}" class="w-full h-full object-cover">
        </div>
        <div class="flex-1 min-w-0 pr-6">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-bold text-white capitalize">${item.fit_status === 'perfect' ? 'Ideal Moslik' : item.fit_status === 'tight' ? 'Tor' : 'Katta'}</span>
            <span class="text-[10px] text-zinc-400">${item.match_percentage}%</span>
          </div>
          <p class="text-[11px] text-zinc-400 mt-1 line-clamp-2">${item.fit_advice || ''}</p>
          <p class="text-[10px] text-zinc-500 mt-2">${new Date(item.created_at).toLocaleString('uz-UZ')}</p>
        </div>
        <button onclick="deleteOneHistory(${item.id})" class="absolute top-3 right-3 text-zinc-500 hover:text-red-400 p-1">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
    `).join('');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Tarixni yuklashda xatolik:", err);
  }
}

async function deleteOneHistory(id) {
  if (!confirm("Ushbu yozuvni tarixdan o'chirasizmi?")) return;
  await fetch(`/api/history/${id}`, { method: 'DELETE' });
  loadHistory();
}

async function clearHistory() {
  if (!confirm("Barcha tarixni tozalashni xohlaysizmi?")) return;
  await fetch('/api/history', { method: 'DELETE' });
  loadHistory();
}

// Profilni saqlash
async function saveProfile(e) {
  e.preventDefault();
  const body = {
    full_name: document.getElementById('prof-name').value,
    height_cm: document.getElementById('prof-height').value,
    weight_kg: document.getElementById('prof-weight').value,
    preferred_size: document.getElementById('prof-size').value
  };

  try {
    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById('header-user-name').innerText = data.profile.full_name;
      alert("Profil muvaffaqiyatli saqlandi!");
    }
  } catch (err) {
    alert("Profilni saqlashda xatolik: " + err.message);
  }
}
