/**
 * 초고정밀 OCR 시스템 파일 업로드 처리
 * 파일 업로드 UI 및 관련 기능 제공
 * 버전: 1.0.0
 */

// Dropzone 설정 및 초기화
let myDropzone;

// 파일 업로드 처리
function initializeUploader() {
  const uploadForm = document.getElementById('upload-form');
  const uploadBtn = document.getElementById('upload-btn');
  const progressArea = document.getElementById('progress-area');
  const progressBar = document.getElementById('progress-bar');
  const statusMessage = document.getElementById('status-message');
  const cancelBtn = document.getElementById('cancel-btn');
  
  // Dropzone 자동 발견 비활성화
  if (typeof Dropzone !== 'undefined') {
    Dropzone.autoDiscover = false;
  }
  
  // Dropzone 인스턴스가 없고 드롭존 요소가 있는 경우에만 초기화
  const dropzoneElement = document.getElementById('document-dropzone');
  if (typeof Dropzone !== 'undefined' && dropzoneElement && !myDropzone) {
    myDropzone = new Dropzone("#document-dropzone", {
      url: "/upload",
      autoProcessQueue: false,
      uploadMultiple: false,
      maxFiles: 1,
      maxFilesize: 20, // MB
      acceptedFiles: ".pdf,.jpg,.jpeg,.png,.tiff,.tif,.bmp,.gif",
      addRemoveLinks: true,
      dictDefaultMessage: "<i class='fas fa-file-upload fa-3x mb-3'></i><br>파일을 끌어다 놓거나<br>클릭하여 선택하세요",
      dictFileTooBig: "파일이 너무 큽니다 ({{filesize}}MB). 최대 파일 크기: {{maxFilesize}}MB.",
      dictInvalidFileType: "이 유형의 파일은 업로드할 수 없습니다.",
      dictResponseError: "서버 응답: {{statusCode}} {{statusText}}",
      dictCancelUpload: "업로드 취소",
      dictUploadCanceled: "업로드가 취소되었습니다.",
      dictRemoveFile: "파일 제거",
      dictMaxFilesExceeded: "더 이상 파일을 업로드할 수 없습니다."
    });
    
    // 파일 추가 이벤트
    myDropzone.on("addedfile", function(file) {
      console.log("파일 추가됨:", file.name);
      if (uploadBtn) {
        uploadBtn.disabled = false;
      }
      
      // 파일 유형에 따라 아이콘 표시
      const fileTypeIcon = getFileTypeIcon(file.type, file.name);
      file.previewElement.querySelector(".dz-details").innerHTML += `<div class="file-type-icon my-2"><i class="${fileTypeIcon} fa-2x"></i></div>`;
    });
    
    // 파일 제거 이벤트
    myDropzone.on("removedfile", function(file) {
      console.log("파일 제거됨:", file.name);
      if (uploadBtn && myDropzone.files.length === 0) {
        uploadBtn.disabled = true;
      }
    });
    
    // 업로드 에러 이벤트
    myDropzone.on("error", function(file, errorMessage) {
      console.error("업로드 오류:", errorMessage);
      if (progressArea) {
        progressArea.classList.add('d-none');
      }
      showAlert("오류가 발생했습니다: " + errorMessage, "danger");
    });
    
    // 업로드 진행 이벤트
    myDropzone.on("uploadprogress", function(file, progress) {
      if (progressBar) {
        progressBar.style.width = Math.min(progress, 90) + '%';
      }
      if (statusMessage && progress > 80) {
        statusMessage.textContent = 'OCR 처리 중...';
      }
    });
    
    // 성공 이벤트
    myDropzone.on("success", function(file, response) {
      console.log("업로드 성공:", response);
      if (statusMessage) {
        statusMessage.textContent = 'OCR 처리 완료! 결과 페이지로 이동합니다...';
      }
      if (progressBar) {
        progressBar.style.width = '100%';
      }
      
      // 응답에서 작업 ID 추출
      const taskId = response.task_id;
      
      // 결과 페이지로 리다이렉트
      setTimeout(function() {
        window.location.href = '/result/' + taskId;
