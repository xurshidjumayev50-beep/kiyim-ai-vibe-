// Kiyim AI Mobile Client Script
let selectedGarmentUrl = null;
let selectedSize = 'M';
let userImageBlob = null;
let garmentImageBlob = null;
let cameraStream = null;
let wardrobeItems = [];

// 2-Bosqich: Tana o'lchamlari va moslik holati
let currentBodyMetrics = null;
let currentLandmarks = null;
let currentFitResults = null;
let isMeasuring = false;

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  loadWardrobe();
  loadHistory();
  updateTryOnButtonState();
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

  if (tabName === 'wardrobe') {
    loadWardrobe();
  }

  if (window.lucide) lucide.createIcons();
}

// O'lcham tanlash (XS - XXL)
async function chooseSize(size, btnElement) {
  selectedSize = size;
  document.querySelectorAll('.size-btn').forEach(btn => {
    btn.className = 'size-btn py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-400 hover:border-zinc-600 transition';
  });
  if (btnElement) {
    btnElement.className = 'size-btn py-2.5 rounded-xl bg-indigo-600 border border-indigo-400 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 transition';
  }
  
  const sizeDisplay = document.getElementById('current-size-display');
  if (sizeDisplay) {
    if (currentFitResults && currentFitResults.recommended_size) {
      sizeDisplay.innerText = `${size} (Tavsiya: ${currentFitResults.recommended_size})`;
    } else {
      sizeDisplay.innerText = `${size}`;
    }
  }

  // Agar tana o'lchovlari mavjud bo'lsa, tanlangan yangi o'lcham bo'yicha moslikni qayta hisoblash
  if (currentBodyMetrics) {
    await recalculateFitForSize(size);
  }
}

// Jins tanlash (Erkak / Ayol)
function setGender(gender) {
  const genderInput = document.getElementById('user-gender-input');
  if (genderInput) genderInput.value = gender;

  const maleBtn = document.getElementById('gender-male-btn');
  const femaleBtn = document.getElementById('gender-female-btn');

  if (gender === 'male') {
    if (maleBtn) maleBtn.className = 'gender-btn py-1 px-1.5 rounded-xl text-[11px] font-semibold bg-indigo-600 text-white border border-indigo-400 flex items-center justify-center space-x-1 transition shadow-sm';
    if (femaleBtn) femaleBtn.className = 'gender-btn py-1 px-1.5 rounded-xl text-[11px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700/60 hover:text-white flex items-center justify-center space-x-1 transition';
  } else {
    if (femaleBtn) femaleBtn.className = 'gender-btn py-1 px-1.5 rounded-xl text-[11px] font-semibold bg-indigo-600 text-white border border-indigo-400 flex items-center justify-center space-x-1 transition shadow-sm';
    if (maleBtn) maleBtn.className = 'gender-btn py-1 px-1.5 rounded-xl text-[11px] font-semibold bg-zinc-800 text-zinc-400 border border-zinc-700/60 hover:text-white flex items-center justify-center space-x-1 transition';
  }

  handleBodyParamChange();
}

function handleBodyParamChange() {
  if (userImageBlob) {
    analyzeBodyMeasurements();
  }
}

// MediaPipe orqali tana o'lchamlarini hisoblash (POST /api/measure)
async function analyzeBodyMeasurements() {
  if (!userImageBlob || isMeasuring) return;

  const gender = document.getElementById('user-gender-input')?.value || 'male';
  const heightVal = parseFloat(document.getElementById('user-height-input')?.value || 0);
  const weightVal = parseFloat(document.getElementById('user-weight-input')?.value || 0);

  if (!heightVal || heightVal <= 0 || !weightVal || weightVal <= 0) {
    alert("Iltimos, bo'y (sm) va vazn (kg) maydonlarini to'ldiring.");
    return;
  }

  isMeasuring = true;
  try {
    const formData = new FormData();
    formData.append('image', userImageBlob, 'person.jpg');
    formData.append('gender', gender);
    formData.append('height', heightVal);
    formData.append('weight', weightVal);
    formData.append('size', selectedSize);

    const res = await fetch('/api/measure', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!data.success) {
      alert(data.error || "Tana o'lchamlarini aniqlashda xatolik yuz berdi");
      return;
    }

    currentBodyMetrics = data.body;
    currentLandmarks = data.landmarks;
    currentFitResults = data.fit;

    console.log("Tana o'lchamlari (sm):", currentBodyMetrics);
    console.log("Fit tahlili:", currentFitResults);

    // O'lcham tavsiyasini yangilash
    if (currentFitResults && currentFitResults.recommended_size) {
      const recEl = document.getElementById('current-size-display');
      if (recEl) {
        recEl.innerText = `${selectedSize} (Tavsiya: ${currentFitResults.recommended_size})`;
      }
    }
  } catch (err) {
    console.error("Tana o'lchami so'rovida xatolik:", err);
  } finally {
    isMeasuring = false;
  }
}

// O'lcham o'zgarganda fit natijasini qayta hisoblash
async function recalculateFitForSize(size) {
  if (!currentBodyMetrics) return;

  try {
    const res = await fetch('/api/measure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        body: currentBodyMetrics,
        landmarks: currentLandmarks,
        size: size
      })
    });

    const data = await res.json();
    if (data.success) {
      currentFitResults = data.fit;
      console.log(`${size} bo'yicha fit yangilandi:`, currentFitResults);

      const recEl = document.getElementById('current-size-display');
      if (recEl && currentFitResults.recommended_size) {
        recEl.innerText = `${size} (Tavsiya: ${currentFitResults.recommended_size})`;
      }
    }
  } catch (e) {
    console.error("O'lcham qayta hisoblashda xatolik:", e);
  }
}

// Rasm tekshiruvi (jpg/png/webp, maks 10MB) va Canvas orqali ~1024px ga kichraytirish
async function processImageFile(file, maxDimension = 1024) {
  if (!file) throw new Error("Fayl tanlanmadi");

  const validMimes = ['image/jpeg', 'image/png', 'image/webp'];
  const validExts = ['.jpg', '.jpeg', '.png', '.webp'];
  const ext = '.' + (file.name ? file.name.split('.').pop().toLowerCase() : '');

  const mimeValid = validMimes.includes(file.type);
  const extValid = validExts.includes(ext);

  if (!mimeValid && !extValid) {
    throw new Error("Faqat JPG, PNG yoki WEBP formatidagi rasmlar qabul qilinadi!");
  }

  if (file.size > 10 * 1024 * 1024) {
    throw new Error("Rasm hajmi 10 MB dan oshmasligi kerak!");
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Rasmni o'qishda xatolik yuz berdi"));
    reader.onload = (e) => {
      const img = new Image();
      img.onerror = () => reject(new Error("Rasmni yuklashda xatolik yuz berdi"));
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > maxDimension || height > maxDimension) {
          if (width > height) {
            height = Math.round((height * maxDimension) / width);
            width = maxDimension;
          } else {
            width = Math.round((width * maxDimension) / height);
            height = maxDimension;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob((blob) => {
          if (!blob) {
            return reject(new Error("Rasmni siqishda xatolik yuz berdi"));
          }
          const resizedDataUrl = canvas.toDataURL('image/jpeg', 0.9);
          resolve({ blob, dataUrl: resizedDataUrl });
        }, 'image/jpeg', 0.9);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// Slot bosilganda yuklashni boshlash
function triggerUserUpload() {
  if (!userImageBlob) {
    document.getElementById('user-file-input').click();
  }
}

function triggerGarmentUpload() {
  if (!garmentImageBlob && !selectedGarmentUrl) {
    document.getElementById('garment-file-input').click();
  }
}

// Foydalanuvchi rasmini tanlash
async function handleUserFileSelect(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  try {
    const { blob, dataUrl } = await processImageFile(file, 1024);
    userImageBlob = blob;

    const imgEl = document.getElementById('user-img-element');
    imgEl.src = dataUrl;
    imgEl.classList.remove('hidden');

    document.getElementById('user-empty-placeholder').classList.add('hidden');
    document.getElementById('user-empty-controls').classList.add('hidden');

    const loadedControls = document.getElementById('user-loaded-controls');
    loadedControls.classList.remove('hidden');
    loadedControls.classList.add('flex');

    updateTryOnButtonState();
    if (window.lucide) lucide.createIcons();

    // Tana o'lchamlarini MediaPipe orqali aniqlash
    analyzeBodyMeasurements();
  } catch (err) {
    alert(err.message);
  } finally {
    event.target.value = '';
  }
}

// Foydalanuvchi rasmini o'chirish
function clearUserImage() {
  userImageBlob = null;
  currentBodyMetrics = null;
  currentLandmarks = null;
  currentFitResults = null;

  const imgEl = document.getElementById('user-img-element');
  imgEl.src = '';
  imgEl.classList.add('hidden');

  document.getElementById('user-empty-placeholder').classList.remove('hidden');
  document.getElementById('user-empty-controls').classList.remove('hidden');

  const loadedControls = document.getElementById('user-loaded-controls');
  loadedControls.classList.add('hidden');
  loadedControls.classList.remove('flex');

  const fileInput = document.getElementById('user-file-input');
  if (fileInput) fileInput.value = '';

  const recEl = document.getElementById('current-size-display');
  if (recEl) recEl.innerText = `${selectedSize}`;

  updateTryOnButtonState();
  if (window.lucide) lucide.createIcons();
}

// Kiyim rasmini tanlash (Galereyadan yuklash)
async function handleGarmentFileSelect(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  try {
    const { blob, dataUrl } = await processImageFile(file, 1024);
    garmentImageBlob = blob;
    selectedGarmentUrl = null;

    const imgEl = document.getElementById('garment-img-element');
    imgEl.src = dataUrl;
    imgEl.classList.remove('hidden');

    document.getElementById('garment-empty-placeholder').classList.add('hidden');
    document.getElementById('garment-empty-controls').classList.add('hidden');

    const loadedControls = document.getElementById('garment-loaded-controls');
    loadedControls.classList.remove('hidden');
    loadedControls.classList.add('flex');

    // Katalog kartalari belgisini yechish
    document.querySelectorAll('.garment-card').forEach(c => {
      c.classList.remove('ring-2', 'ring-indigo-500', 'border-transparent');
      c.classList.add('border-zinc-800');
    });

    // Avtomatik ravishda Garderob / Katalogga saqlash
    saveGarmentToWardrobe(blob, file.name);

    updateTryOnButtonState();
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    alert(err.message);
  } finally {
    event.target.value = '';
  }
}

// Kiyim rasmini o'chirish
function clearGarmentImage() {
  garmentImageBlob = null;
  selectedGarmentUrl = null;

  const imgEl = document.getElementById('garment-img-element');
  imgEl.src = '';
  imgEl.classList.add('hidden');

  document.getElementById('garment-empty-placeholder').classList.remove('hidden');
  document.getElementById('garment-empty-controls').classList.remove('hidden');

  const loadedControls = document.getElementById('garment-loaded-controls');
  loadedControls.classList.add('hidden');
  loadedControls.classList.remove('flex');

  // Katalog kartalari belgisini yechish
  document.querySelectorAll('.garment-card').forEach(c => {
    c.classList.remove('ring-2', 'ring-indigo-500', 'border-transparent');
    c.classList.add('border-zinc-800');
  });

  const fileInput = document.getElementById('garment-file-input');
  if (fileInput) fileInput.value = '';

  updateTryOnButtonState();
  if (window.lucide) lucide.createIcons();
}

// Katalogdan kiyim tanlash
function selectGarment(imageUrl, title, cardElement) {
  selectedGarmentUrl = imageUrl;
  garmentImageBlob = null;

  const imgEl = document.getElementById('garment-img-element');
  imgEl.src = imageUrl;
  imgEl.classList.remove('hidden');

  document.getElementById('garment-empty-placeholder').classList.add('hidden');
  document.getElementById('garment-empty-controls').classList.add('hidden');

  const loadedControls = document.getElementById('garment-loaded-controls');
  loadedControls.classList.remove('hidden');
  loadedControls.classList.add('flex');

  document.querySelectorAll('.garment-card').forEach(c => {
    c.classList.remove('ring-2', 'ring-indigo-500', 'border-transparent');
    c.classList.add('border-zinc-800');
  });

  if (cardElement) {
    cardElement.classList.add('ring-2', 'ring-indigo-500', 'border-transparent');
    cardElement.classList.remove('border-zinc-800');
  }

  updateTryOnButtonState();
  if (window.lucide) lucide.createIcons();
}

function useInStudio(imageUrl, title) {
  selectGarment(imageUrl, title, null);
  switchTab('studio');
}

// Garderobga / Serverga saqlash
async function saveGarmentToWardrobe(blob, originalName) {
  try {
    const formData = new FormData();
    formData.append('image', blob, 'garment.jpg');
    const title = originalName ? originalName.replace(/\.[^/.]+$/, "") : `Kiyim ${wardrobeItems.length + 1}`;
    formData.append('title', title || `Kiyim ${wardrobeItems.length + 1}`);
    formData.append('category', 'upper_body');

    const res = await fetch('/api/garments', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      await loadWardrobe();
      if (!selectedGarmentUrl && data.image_url) {
        selectedGarmentUrl = data.image_url;
      }
    }
  } catch (err) {
    console.error("Garderobga saqlashda xatolik:", err);
  }
}

// Garderobdan yangi kiyim yuklash (+ Tugmasi orqali)
async function uploadNewGarment(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  try {
    const { blob } = await processImageFile(file, 1024);
    const formData = new FormData();
    formData.append('image', blob, 'garment.jpg');
    const title = file.name ? file.name.replace(/\.[^/.]+$/, "") : `Kiyim ${wardrobeItems.length + 1}`;
    formData.append('title', title);
    formData.append('category', 'upper_body');

    const res = await fetch('/api/garments', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.success) {
      await loadWardrobe();
      alert("Yangi kiyim garderobga muvaffaqiyatli qo'shildi!");
    } else {
      alert("Xatolik: " + (data.error || "Kiyim yuklanmadi"));
    }
  } catch (err) {
    alert(err.message);
  } finally {
    event.target.value = '';
  }
}

// Garderob va Katalog ro'yxatini yuklash va UI ga chiqarish
async function loadWardrobe() {
  try {
    const res = await fetch('/api/garments');
    const data = await res.json();
    wardrobeItems = Array.isArray(data) ? data : [];
    localStorage.setItem('kiyim_wardrobe', JSON.stringify(wardrobeItems));
  } catch (err) {
    console.warn("Garderobni serverdan olishda xatolik, localStoragedan olinmoqda:", err);
    const local = localStorage.getItem('kiyim_wardrobe');
    wardrobeItems = local ? JSON.parse(local) : [];
  }
  renderWardrobeUI();
}

function renderWardrobeUI() {
  const scrollContainer = document.getElementById('wardrobe-scroll');
  const gridContainer = document.getElementById('wardrobe-grid');

  if (wardrobeItems.length === 0) {
    if (scrollContainer) {
      scrollContainer.innerHTML = `
        <div id="wardrobe-scroll-empty" class="w-full py-4 text-center text-xs text-zinc-500 bg-zinc-900/40 rounded-2xl border border-zinc-800/80">
          Hali kiyim yo'q. Galereyadan yuklang
        </div>
      `;
    }
    if (gridContainer) {
      gridContainer.innerHTML = `
        <div id="wardrobe-grid-empty" class="col-span-2 py-12 text-center text-xs text-zinc-500 bg-zinc-900/40 rounded-2xl border border-zinc-800/80">
          Hali kiyim yo'q. Galereyadan yuklang
        </div>
      `;
    }
    if (window.lucide) lucide.createIcons();
    return;
  }

  if (scrollContainer) {
    scrollContainer.innerHTML = wardrobeItems.map(g => {
      const isSelected = selectedGarmentUrl === g.image_url;
      return `
        <div onclick="selectGarment('${g.image_url}', '${g.title}', this)" 
             class="garment-card flex-shrink-0 w-20 bg-zinc-900 border ${isSelected ? 'ring-2 ring-indigo-500 border-transparent' : 'border-zinc-800'} hover:border-indigo-500 rounded-2xl p-2 cursor-pointer transition-all">
          <div class="w-16 h-20 rounded-xl overflow-hidden bg-black/40 flex items-center justify-center mb-1.5">
            <img src="${g.image_url}" class="w-full h-full object-contain">
          </div>
          <p class="text-[10px] font-medium text-zinc-300 truncate text-center">${g.title}</p>
        </div>
      `;
    }).join('');
  }

  if (gridContainer) {
    gridContainer.innerHTML = wardrobeItems.map(g => `
      <div class="bg-zinc-900 border border-zinc-800 rounded-2xl p-3 flex flex-col items-center">
        <div class="w-full h-36 bg-zinc-950 rounded-xl overflow-hidden p-2 flex items-center justify-center mb-2">
          <img src="${g.image_url}" class="w-full h-full object-contain">
        </div>
        <p class="text-xs font-bold text-white truncate w-full text-center">${g.title}</p>
        <p class="text-[10px] text-zinc-500 uppercase mt-0.5">${g.category || 'upper_body'}</p>
        <button onclick="useInStudio('${g.image_url}', '${g.title}')" class="mt-2.5 w-full bg-zinc-800 hover:bg-zinc-700 py-1.5 rounded-xl text-[11px] font-semibold text-indigo-400 transition">
          Kiyib ko'rish
        </button>
      </div>
    `).join('');
  }

  if (window.lucide) lucide.createIcons();
}

// Try-On tugmasini tekshirish (ikkala rasm yuklanmaguncha disabled)
function updateTryOnButtonState() {
  const submitBtn = document.getElementById('tryon-submit-btn');
  const hint = document.getElementById('tryon-btn-hint');

  const hasUser = !!userImageBlob;
  const hasGarment = !!garmentImageBlob || !!selectedGarmentUrl;

  if (hasUser && hasGarment) {
    submitBtn.disabled = false;
    submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    submitBtn.classList.add('hover:from-indigo-500', 'hover:to-violet-500', 'active:scale-[0.98]', 'cursor-pointer');
    if (hint) {
      hint.classList.add('hidden');
    }
  } else {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
    submitBtn.classList.remove('hover:from-indigo-500', 'hover:to-violet-500', 'active:scale-[0.98]', 'cursor-pointer');
    if (hint) {
      hint.classList.remove('hidden');
      hint.innerText = "Avval ikkala rasmni yuklang";
    }
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

  // Max 1024px o'lchamga keltirish
  let w = video.videoWidth;
  let h = video.videoHeight;
  const maxDim = 1024;
  if (w > maxDim || h > maxDim) {
    if (w > h) {
      h = Math.round((h * maxDim) / w);
      w = maxDim;
    } else {
      w = Math.round((w * maxDim) / h);
      h = maxDim;
    }
  }

  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, w, h);

  canvas.toBlob(blob => {
    userImageBlob = blob;
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);

    const imgEl = document.getElementById('user-img-element');
    imgEl.src = dataUrl;
    imgEl.classList.remove('hidden');

    document.getElementById('user-empty-placeholder').classList.add('hidden');
    document.getElementById('user-empty-controls').classList.add('hidden');

    const loadedControls = document.getElementById('user-loaded-controls');
    loadedControls.classList.remove('hidden');
    loadedControls.classList.add('flex');

    stopCamera();
    switchTab('studio');
    updateTryOnButtonState();
    if (window.lucide) lucide.createIcons();

    // Tana o'lchamlarini hisoblash
    analyzeBodyMeasurements();
  }, 'image/jpeg', 0.9);
}

let lastOriginalImageUrl = '';
let lastResultImageUrl = '';

// Asosiy Try-On jarayoni
async function executeTryOn() {
  const loading = document.getElementById('tryon-loading');
  const submitBtn = document.getElementById('tryon-submit-btn');
  const resultBox = document.getElementById('tryon-result-box');

  const hasUser = !!userImageBlob;
  const hasGarment = !!garmentImageBlob || !!selectedGarmentUrl;

  if (!hasUser || !hasGarment) {
    alert("Avval ikkala rasmni yuklang");
    return;
  }

  loading.classList.remove('hidden');
  resultBox.classList.add('hidden');
  submitBtn.disabled = true;

  try {
    const formData = new FormData();
    formData.append('user_image', userImageBlob, 'user.jpg');

    if (garmentImageBlob) {
      formData.append('garment_image', garmentImageBlob, 'garment.jpg');
    } else if (selectedGarmentUrl) {
      formData.append('garment_url', selectedGarmentUrl);
    }

    formData.append('selected_size', selectedSize);

    // Tana parametrlari
    const heightEl = document.getElementById('body-height-input');
    const weightEl = document.getElementById('body-weight-input');
    const genderEl = document.getElementById('body-gender-select');

    const heightVal = heightEl ? heightEl.value : (currentUserProfile.height_cm || 175);
    const weightVal = weightEl ? weightEl.value : (currentUserProfile.weight_kg || 70);
    const genderVal = genderEl ? genderEl.value : (currentUserProfile.gender || 'male');

    formData.append('height_cm', heightVal);
    formData.append('weight_kg', weightVal);
    formData.append('gender', genderVal);

    const res = await fetch('/api/tryon', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || "Try-On ishlovida xatolik");
    }

    // Natijalarni ko'rsatish
    lastResultImageUrl = data.result_image_url;
    lastOriginalImageUrl = data.user_image_url;

    const resultImg = document.getElementById('result-img-element');
    if (resultImg) {
      resultImg.src = lastResultImageUrl;
    }

    // Dinamik qiymatlarni yangilash (Backenddan olingan o'zgaruvchilar)
    const fitPercentEl = document.getElementById('fit-percent');
    const fitBarEl = document.getElementById('fit-bar');
    const fitAdviceEl = document.getElementById('fit-advice-text');
    const fitRecSizeEl = document.getElementById('fit-rec-size');

    if (fitPercentEl) {
      fitPercentEl.innerText = data.match_percentage != null ? `${data.match_percentage}%` : '--%';
    }
    if (fitBarEl) {
      fitBarEl.style.width = data.match_percentage != null ? `${data.match_percentage}%` : '0%';
    }
    if (fitAdviceEl) {
      fitAdviceEl.innerText = data.fit_advice || 'Tahlil kutilmoqda';
    }
    if (fitRecSizeEl) {
      fitRecSizeEl.innerText = data.recommended_size ? `Tavsiya etilgan o'lcham: ${data.recommended_size}` : 'Tavsiya etilgan o'lcham: --';
    }

    // Fit Badge
    const badge = document.getElementById('fit-badge');
    if (badge) {
      if (data.fit_status === 'perfect' || data.fit_status === 'ok') {
        badge.innerText = 'Ideal Moslik';
        badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
      } else if (data.fit_status === 'tight') {
        badge.innerText = 'Tor';
        badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30';
      } else if (data.fit_status === 'loose' || data.fit_status === 'oversize') {
        badge.innerText = 'Katta / Oversized';
        badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30';
      } else {
        badge.innerText = 'Tahlil kutilmoqda';
        badge.className = 'px-2.5 py-0.5 rounded-full text-xs font-bold bg-zinc-800 text-zinc-400 border border-zinc-700/60';
      }
    }

    resultBox.classList.remove('hidden');
    resultBox.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    alert("Xatolik: " + err.message);
  } finally {
    loading.classList.add('hidden');
    updateTryOnButtonState();
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
