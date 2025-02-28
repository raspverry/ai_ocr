/**
 * 초고정밀 OCR 시스템 메인 자바스크립트 파일
 * 전역 기능 및 유틸리티 함수 제공
 * 버전: 1.0.0
 */

// 사용자 알림 표시
function showAlert(message, type = 'info', duration = 5000) {
  // 알림 타입: success, danger, warning, info
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.role = 'alert';
  
  // Font Awesome 아이콘 추가
  let icon = 'info-circle';
  if (type === 'success') icon = 'check-circle';
  if (type === 'danger') icon = 'exclamation-triangle';
  if (type === 'warning') icon = 'exclamation-circle';
  
  alertDiv.innerHTML = `
    <i class="fas fa-${icon} me-2"></i> ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  
  // 문서에 알림 추가
  const container = document.querySelector('.container');
  container.insertBefore(alertDiv, container.firstChild);
  
  // 지정된 시간 후 자동 제거
  if (duration > 0) {
    setTimeout(() => {
      alertDiv.classList.remove('show');
      setTimeout(() => alertDiv.remove(), 300);
    }, duration);
  }
  
  return alertDiv;
}

// 문자열을 클립보드에 복사
function copyToClipboard(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
  
  // 복사 성공 알림
  showAlert('클립보드에 복사되었습니다.', 'success', 2000);
}

// 날짜 포맷 (YYYY-MM-DD HH:MM)
function formatDate(dateStr) {
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) {
    return dateStr; // 유효하지 않은 날짜는 그대로 반환
  }
  
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

// 파일 크기 포맷 (바이트 → 읽기 쉬운 형식)
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 언어 코드를 사람이 읽기 쉬운 언어명으로 변환
function formatLanguage(langCode) {
  const languages = {
    'jpn': '일본어',
    'eng': '영어',
    'kor': '한국어',
    'chi_sim': '중국어 간체',
    'chi_tra': '중국어 번체'
  };
  
  return languages[langCode] || langCode;
}

// URL에서 매개변수 추출
function getUrlParameter(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

// 문서 준비 완료
document.addEventListener('DOMContentLoaded', function() {
  // 모든 토글 가능한 툴팁 초기화
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  if (tooltips.length > 0) {
    tooltips.forEach(tooltip => {
      new bootstrap.Tooltip(tooltip);
    });
  }
  
  // 모든 팝오버 초기화
  const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
  if (popovers.length > 0) {
    popovers.forEach(popover => {
      new bootstrap.Popover(popover);
    });
  }
  
  // 네비게이션 바 활성 링크 처리
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
  
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
      link.classList.add('active');
    }
  });
  
  // 세션 만료 확인 및 처리
  const lastActivityTime = localStorage.getItem('lastActivityTime');
  const currentTime = Date.now();
  const sessionTimeout = 3600000; // 1시간 (밀리초)
  
  if (lastActivityTime && (currentTime - lastActivityTime) > sessionTimeout) {
    // 세션 만료 처리
    showAlert('세션이 만료되었습니다. 다시 로그인해주세요.', 'warning');
    setTimeout(() => {
      window.location.href = '/login';
    }, 2000);
  } else {
    // 활동 시간 업데이트
    localStorage.setItem('lastActivityTime', currentTime);
  }
  
  // 페이지 로드 완료 로그
  console.log('페이지 로드 완료');
});

// 사용자 활동 감지 및 세션 시간 업데이트
['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
  document.addEventListener(event, () => {
    localStorage.setItem('lastActivityTime', Date.now());
  }, { passive: true });
});
