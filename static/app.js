const $ = id => document.getElementById(id);
let file = null, previewURL = '', busy = false, sampleBrief = false;
let currentStep = 1;
const instructionDefaults = {
  'gemini-instructions': $('gemini-instructions').value,
  'chatgpt-instructions': $('chatgpt-instructions').value,
};
function showStep(step, focusPanel = false) {
  if (busy) return;
  currentStep = step;
  for (let i = 1; i <= 3; i++) {
    $(`stage${i}`).hidden = i !== step;
    $(`step${i}`).classList.toggle('active', i === step);
    $(`step${i}`).setAttribute('aria-selected', String(i === step));
    $(`step${i}`).tabIndex = i === step ? 0 : -1;
  }
  if (focusPanel) {
    $(`stage${step}`).tabIndex = -1;
    $(`stage${step}`).focus({preventScroll: true});
    document.querySelector('.workflow').scrollIntoView({block: 'start', behavior: 'smooth'});
  }
}
document.querySelectorAll('[data-step]').forEach(button => {
  button.addEventListener('click', () => showStep(Number(button.dataset.step)));
  button.addEventListener('keydown', e => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key) || busy) return;
    e.preventDefault();
    const step = e.key === 'Home' ? 1 : e.key === 'End' ? 3 : ((currentStep - 1 + (e.key === 'ArrowRight' ? 1 : 2)) % 3) + 1;
    showStep(step); $(`step${step}`).focus();
  });
});
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => showStep(Number(button.dataset.go), true)));
$('skip-video').addEventListener('click', e => { e.preventDefault(); showStep(2, true); });
for (const id of ['connection', 'settings-open']) $(id).addEventListener('click', () => $('settings-dialog').showModal());
$('help-open').addEventListener('click', () => $('help-dialog').showModal());
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
document.querySelectorAll('.reset-instructions').forEach(button => button.addEventListener('click', () => {
  const field = $(button.dataset.field);
  if (field.value !== instructionDefaults[field.id] && field.value.trim() && !confirm('Thay hướng dẫn hiện tại bằng nội dung mẫu?')) return;
  field.value = instructionDefaults[field.id];
  field.dispatchEvent(new Event('input')); field.focus();
}));
const demoBrief = `## BẢN MẪU MINH HỌA — không phải kết quả phân tích video
## 1. Tóm tắt & mục tiêu
Video giả định 15 giây giới thiệu cà phê buổi sáng, tạo cảm giác thư thái.
## 2. Khán giả & thông điệp
Người đi làm 25–35 tuổi. Thông điệp: dành một khoảng lặng cho chính mình.
## 3. Hook
Cận cảnh giọt cà phê chạm mặt nước, ánh sáng ban mai.
## 4. Phân cảnh
0–3s: Macro giọt cà phê, âm thanh nhỏ giọt, máy tĩnh.
3–8s: Trung cảnh bàn gỗ cạnh cửa sổ, hơi nước bay, máy tiến chậm.
8–12s: Nhân vật nâng ly, ánh sáng ấm, nhịp dựng nhẹ.
12–15s: Ly cà phê trên bàn, khoảng trống cho CTA mới.
## 5. Phong cách
Tông nâu và kem, ánh sáng mềm, nhạc acoustic nhẹ.
## 6. Hướng phát triển
Thay bối cảnh bằng một xưởng gốm; xây câu chuyện mới về sự tập trung. Không dùng logo hoặc lời thoại của video tham chiếu.`;
const demoPrompt = `# PROMPT MẪU MINH HỌA — không gọi Gemini hoặc ChatGPT

## Concept: A moment before the day
An original 15-second coffee film set in a sunlit pottery studio.

## Master prompt (English)
Create a cinematic short film in a quiet pottery studio at sunrise. An anonymous ceramic artist pauses before work and pours coffee into a handmade ivory cup. Warm natural light, soft steam, tactile clay textures, restrained earth tones. Slow, deliberate camera movement. Intimate, calm mood. Maintain the same cup, hands and window light across shots. No logos, no watermarks, no imitation of a specific advertisement.

## Shots
0–3s: Macro, coffee pours into a handmade cup, shallow depth of field.
3–8s: Slow camera push toward a wooden workbench, unfinished pottery in the background.
8–12s: Close-up of hands wrapping around the warm cup, steam catching the light.
12–15s: Still life of the cup beside a clay bowl. Leave negative space for a separately edited CTA.

## Production notes
Suggested framing: 9:16. Generate shots separately, then edit into a 15-second sequence. Add subtle studio ambience and music during editing if the selected model does not support audio. Add brand text in post-production for accuracy. Available duration and settings depend on the model version.

Đây là ví dụ cố định để khám phá giao diện. Kết quả API thực tế phụ thuộc video, định hướng và mô hình bạn chọn.`;
function notice(message, error = false) {
  $('notice').textContent = message; $('notice').classList.toggle('error', error); $('notice').hidden = false;
  $('notice').classList.toggle('processing', busy && !error);
}
function refresh() {
  $('analyze').disabled = busy || !file;
  $('rewrite').disabled = busy || !$('brief').value.trim();
  for (const id of ['demo', 'video', 'remove', 'brief', 'context', 'target', 'language', 'gemini-instructions', 'chatgpt-instructions']) $(id).disabled = busy;
  document.querySelectorAll('[data-step], [data-go], .reset-instructions').forEach(button => { button.disabled = busy; });
  $('skip-video').setAttribute('aria-disabled', String(busy));
  $('char-count').textContent = `${$('brief').value.length.toLocaleString('vi-VN')} ký tự`;
  $('step1').classList.toggle('done', !!file);
  $('step2').classList.toggle('done', !!$('brief').value.trim());
  $('step3').classList.toggle('done', !!$('result').textContent);
  $('gemini-count').textContent = `${$('gemini-instructions').value.length.toLocaleString('vi-VN')} / 10.000`;
  $('chatgpt-count').textContent = `${$('chatgpt-instructions').value.length.toLocaleString('vi-VN')} / 10.000`;
  $('analyze-hint').textContent = busy && currentStep === 1 ? 'Gemini đang xử lý. Bạn có thể chờ tại đây.' : file ? 'Video đã sẵn sàng. Kiểm tra hướng dẫn rồi bấm phân tích.' : 'Chọn một video để bắt đầu phân tích.';
  $('rewrite-hint').textContent = busy && currentStep === 2 ? 'ChatGPT đang viết prompt theo yêu cầu của bạn.' : $('brief').value.trim() ? 'Bản sơ lược đã sẵn sàng. Bạn có thể tạo prompt.' : 'Thêm bản sơ lược để tạo prompt.';
}
function invalidateOutput() {
  $('result').textContent = ''; $('result').hidden = true; $('empty-output').hidden = false;
  $('copy').disabled = true; $('download').disabled = true; $('output-label').hidden = true;
}
function setFile(next) {
  if (busy) return;
  if (next && (!['video/mp4', 'video/webm', 'video/quicktime', 'video/mpeg'].includes(next.type) || next.size > 100 * 1024 * 1024 || !next.size)) {
    notice('Chọn video MP4, MOV, WebM hoặc MPEG không rỗng, tối đa 100 MB.', true); return;
  }
  if (previewURL) URL.revokeObjectURL(previewURL);
  file = next;
  $('selected').hidden = !file; $('dropzone').hidden = !!file;
  if (file) {
    previewURL = URL.createObjectURL(file); $('preview').src = previewURL;
    $('filename').textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB`;
    $('brief').value = ''; sampleBrief = false; $('brief-label').textContent = 'CÓ THỂ CHỈNH SỬA'; invalidateOutput();
  } else { $('preview').removeAttribute('src'); $('preview').load(); $('video').value = ''; }
  refresh();
}
function showOutput(text, demo = false) {
  $('result').textContent = text; $('result').hidden = false; $('empty-output').hidden = true;
  $('copy').disabled = false; $('download').disabled = false; $('output-label').hidden = !demo; refresh();
}
async function request(path, options) {
  const response = await fetch(path, options);
  let data;
  try { data = await response.json(); } catch { throw new Error('Máy chủ trả phản hồi không hợp lệ. Kiểm tra kết nối.'); }
  if (!response.ok) throw new Error(data.error || 'Yêu cầu thất bại.');
  return data;
}
async function run(id, label, fn) {
  if (busy) return;
  busy = true; const original = $(id).innerHTML; $(id).textContent = label; $(id).classList.add('busy'); refresh();
  try { await fn(); } catch (err) { notice(err.message || 'Mất kết nối. Hãy thử lại.', true); }
  finally { busy = false; $(id).innerHTML = original; $(id).classList.remove('busy'); $('notice').classList.remove('processing'); refresh(); }
}
$('video').addEventListener('change', e => setFile(e.target.files[0] || null));
$('remove').addEventListener('click', () => setFile(null));
for (const event of ['dragover', 'dragleave', 'drop']) $('dropzone').addEventListener(event, e => {
  e.preventDefault(); $('dropzone').classList.toggle('drag', event === 'dragover');
  if (event === 'drop') setFile(e.dataTransfer.files[0] || null);
});
$('brief').addEventListener('input', () => { invalidateOutput(); refresh(); });
$('gemini-instructions').addEventListener('input', refresh);
for (const id of ['context', 'target', 'language', 'chatgpt-instructions']) $(id).addEventListener('input', () => { invalidateOutput(); refresh(); });
$('analyze').addEventListener('click', () => run('analyze', 'Gemini đang phân tích…', async () => {
  notice('Đang gửi video và chờ Gemini xử lý. Video dài có thể mất vài phút.');
  const form = new FormData();
  form.append('video', file);
  form.append('instructions', $('gemini-instructions').value);
  const data = await request('/api/analyze', {method: 'POST', body: form});
  $('brief').value = data.text; sampleBrief = false; $('brief-label').textContent = 'GEMINI · CÓ THỂ CHỈNH SỬA'; invalidateOutput();
  notice('Đã phân tích xong. Kiểm tra bản sơ lược, thêm định hướng và tạo prompt.');
  busy = false; showStep(2, true);
}));
$('rewrite').addEventListener('click', () => run('rewrite', 'ChatGPT đang viết prompt…', async () => {
  invalidateOutput();
  notice(sampleBrief ? 'Đang gửi bản sơ lược mẫu tới ChatGPT thật. Yêu cầu này sử dụng API và có thể phát sinh phí.' : 'Đang chuyển bản sơ lược thành prompt qua ChatGPT…');
  const data = await request('/api/rewrite', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({brief: $('brief').value, context: $('context').value, target: $('target').value, language: $('language').value,
      instructions: $('chatgpt-instructions').value})});
  showOutput(data.text); notice('Prompt đã sẵn sàng. Kiểm tra và điều chỉnh thông số theo phiên bản mô hình đích.');
  busy = false; showStep(3, true);
}));
$('demo').addEventListener('click', () => {
  if (($('brief').value.trim() || $('result').textContent) && !confirm('Thay nội dung hiện tại bằng dữ liệu mẫu?')) return;
  $('brief').value = demoBrief; sampleBrief = true; $('brief-label').textContent = 'DỮ LIỆU MẪU';
  showOutput(demoPrompt, true); notice('Đang xem ví dụ cố định, chưa gọi API. Nút “Tạo prompt bằng ChatGPT” sẽ gọi API thật với bản sơ lược hiện tại.');
  showStep(3, true);
});
$('copy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('result').textContent); notice('Đã sao chép prompt.'); }
  catch { notice('Trình duyệt không cho sao chép tự động. Chọn nội dung prompt và sao chép thủ công.', true); }
});
$('download').addEventListener('click', () => {
  const url = URL.createObjectURL(new Blob([$('result').textContent], {type: 'text/markdown;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = 'frameflow-prompt.md'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
request('/api/status').then(status => {
  $('connection').textContent = status.gemini && status.openai ? '● Đã cấu hình khóa API' : '○ Cần cấu hình API';
  $('connection').classList.toggle('ready', status.gemini && status.openai);
  $('sidebar-status').classList.toggle('ready', status.gemini && status.openai);
  $('gemini-status').textContent = status.gemini ? 'Đã cấu hình khóa' : 'Chưa cấu hình khóa';
  $('openai-status').textContent = status.openai ? 'Đã cấu hình khóa' : 'Chưa cấu hình khóa';
  $('gemini-status').classList.toggle('ready', status.gemini);
  $('openai-status').classList.toggle('ready', status.openai);
  $('model-info').textContent = `Mô hình: Gemini ${status.gemini_model} / OpenAI ${status.openai_model}. Trạng thái chỉ kiểm tra sự hiện diện của khóa; kết nối được xác minh khi gửi yêu cầu thực tế.`;
}).catch(() => {
  $('connection').textContent = '○ Mất kết nối máy chủ';
  $('gemini-status').textContent = $('openai-status').textContent = 'Không kiểm tra được trạng thái';
});
showStep(1);
refresh();
