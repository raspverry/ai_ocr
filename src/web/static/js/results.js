/**
 * 초고정밀 OCR 시스템 결과 페이지 스크립트
 * 결과 페이지 기능 및 상호작용 처리
 * 버전: 1.0.0
 */

// 문서 준비 완료 시
document.addEventListener('DOMContentLoaded', function() {
  // 처리 상태 확인
  const statusElement = document.querySelector('[data-status]');
  if (statusElement) {
    const status = statusElement.dataset.status;
    
    // 처리 중인 경우 자동 새로고침 설정
    if (status === 'processing') {
      startAutoRefresh();
    }
  }
  
  // 탭 전환 이벤트 처리
  const resultTabs = document.getElementById('resultTab');
  if (resultTabs) {
    resultTabs.addEventListener('shown.bs.tab', function(event) {
      // 새 탭 활성화 시 (Bootstrap 5 이벤트)
      const activeTab = event.target.id;
      console.log('탭 변경:', activeTab);
      
      // 탭 상태 세션 스토리지에 저장 (페이지 새로고침 후에도 유지)
      sessionStorage.setItem('activeResultTab', activeTab);
    });
    
    // 저장된 탭 상태 복원
    const savedTab = sessionStorage.getItem('activeResultTab');
    if (savedTab) {
      // Bootstrap 5 탭 수동 활성화
      const tabElement = document.getElementById(savedTab);
      if (tabElement) {
        const tab = new bootstrap.Tab(tabElement);
        tab.show();
      }
    }
  }
  
  // 텍스트 복사 버튼 이벤트 연결
  setupCopyButtons();
  
  // 이미지 확대/축소 기능 초기화
  initializeImageZoom();
  
  // 특수 항목 강조 표시 초기화
  initializeSpecialItems();
});

/**
 * 자동 새로고침 기능
 */
function startAutoRefresh() {
  const refreshInterval = 5000; // 5초마다 새로고침
  const maxRefreshCount = 60; // 최대 5분 (60회) 동안 시도
  const progressBar = document.querySelector('.progress-bar');
  
  let refreshCount = 0;
  
  const refreshTimer = setInterval(function() {
    refreshCount++;
    
    // 진행 표시줄 업데이트
    if (progressBar) {
      // 진행 시각화를 위한 애니메이션 - 100%까지 천천히 증가
      const progress = Math.min(refreshCount / maxRefreshCount * 100, 90);
      progressBar.style.width = progress + '%';
    }
    
    // 최대 시도 횟수 초과 시 타이머 중지 (5분)
    if (refreshCount >= maxRefreshCount) {
      clearInterval(refreshTimer);
      
      // 오류 메시지 표시
      const processingElement = document.querySelector('.processing');
      if (processingElement) {
        processingElement.innerHTML = `
          <div class="alert alert-warning">
            <h5 class="alert-heading"><i class="fas fa-exclamation-triangle me-2"></i> 처리 시간 초과</h5>
            <p>OCR 처리가 예상보다 오래 걸리고 있습니다. 문서 크기가 크거나 복잡할 수 있습니다.</p>
            <div class="mt-3">
              <button class="btn btn-primary" onclick="window.location.reload()">
                <i class="fas fa-sync-alt"></i> 수동 새로고침
              </button>
              <a href="/documents" class="btn btn-outline-secondary ms-2">
                <i class="fas fa-list"></i> 문서 목록으로
              </a>
            </div>
          </div>
        `;
      }
      
      return;
    }
    
    // 페이지 새로고침
    window.location.reload();
  }, refreshInterval);
  
  // 페이지 이탈 시 타이머 정리
  window.addEventListener('beforeunload', function() {
    clearInterval(refreshTimer);
  });
}

/**
 * 텍스트 복사 버튼 설정
 */
function setupCopyButtons() {
  const copyButtons = document.querySelectorAll('[data-copy-target]');
  
  copyButtons.forEach(button => {
    button.addEventListener('click', function() {
      const targetId = button.dataset.copyTarget;
      const textElement = document.getElementById(targetId);
      
      if (textElement) {
        copyToClipboard(textElement.textContent);
        
        // 복사 성공 피드백
        const tooltip = new bootstrap.Tooltip(button, {
          title: '복사됨!',
          trigger: 'manual',
          placement: 'top'
        });
        
        tooltip.show();
        
        // 2초 후 툴팁 제거
        setTimeout(() => {
          tooltip.hide();
        }, 2000);
      }
    });
  });
}

/**
 * 텍스트를 클립보드에 복사
 */
function copyToClipboard(text) {
  // 임시 텍스트 영역 생성
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';  // 화면 밖으로
  textArea.style.left = '-999999px';
  textArea.style.top = '-999999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  // 복사 명령 실행
  let success = false;
  try {
    success = document.execCommand('copy');
  } catch (err) {
    console.error('클립보드 복사 오류:', err);
  }

  // 임시 요소 제거
  document.body.removeChild(textArea);
  
  // 결과 알림 (선택 사항)
  if (success) {
    // 복사 성공 알림
    showToast('텍스트가 클립보드에 복사되었습니다.', 'success');
  } else {
    // 복사 실패 알림
    showToast('텍스트 복사에 실패했습니다.', 'danger');
  }
  
  return success;
}

/**
 * 알림 토스트 표시
 */
function showToast(message, type = 'info') {
  // Bootstrap 토스트 생성
  const toastElement = document.createElement('div');
  toastElement.className = `toast align-items-center text-white bg-${type} border-0`;
  toastElement.setAttribute('role', 'alert');
  toastElement.setAttribute('aria-live', 'assertive');
  toastElement.setAttribute('aria-atomic', 'true');
  
  // 토스트 내용
  toastElement.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        ${message}
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;
  
  // 토스트 컨테이너가 없으면 생성
  let toastContainer = document.querySelector('.toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(toastContainer);
  }
  
  // 토스트 추가 및 표시
  toastContainer.appendChild(toastElement);
  const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
  toast.show();
  
  // 토스트 제거 이벤트
  toastElement.addEventListener('hidden.bs.toast', function() {
    toastElement.remove();
  });
}

/**
 * 이미지 확대/축소 기능 초기화
 */
function initializeImageZoom() {
  const resultImages = document.querySelectorAll('.result-image');
  
  resultImages.forEach(image => {
    // 이미지 클릭 시 모달 표시
    image.addEventListener('click', function() {
      const imgSrc = image.src;
      const pageNum = image.dataset.page || '';
      
      // 모달 생성
      const modalElement = document.createElement('div');
      modalElement.className = 'modal fade';
      modalElement.id = 'imageModal';
      modalElement.setAttribute('tabindex', '-1');
      modalElement.setAttribute('aria-labelledby', 'imageModalLabel');
      modalElement.setAttribute('aria-hidden', 'true');
      
      // 모달 내용
      modalElement.innerHTML = `
        <div class="modal-dialog modal-lg modal-dialog-centered">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="imageModalLabel">페이지 ${pageNum} 이미지</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body text-center">
              <div class="img-zoom-container">
                <img src="${imgSrc}" class="img-fluid" id="zoomImage">
              </div>
              <div class="mt-3">
                <button class="btn btn-sm btn-outline-secondary zoom-in">
                  <i class="fas fa-search-plus"></i> 확대
                </button>
                <button class="btn btn-sm btn-outline-secondary zoom-out">
                  <i class="fas fa-search-minus"></i> 축소
                </button>
                <button class="btn btn-sm btn-outline-secondary zoom-reset">
                  <i class="fas fa-sync"></i> 원본 크기
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
      
      // 모달 추가 및 표시
      document.body.appendChild(modalElement);
      const modal = new bootstrap.Modal(modalElement);
      modal.show();
      
      // 확대/축소 기능
      let scale = 1;
      const zoomImage = document.getElementById('zoomImage');
      
      // 확대 버튼
      modalElement.querySelector('.zoom-in').addEventListener('click', function() {
        scale += 0.2;
        zoomImage.style.transform = `scale(${scale})`;
      });
      
      // 축소 버튼
      modalElement.querySelector('.zoom-out').addEventListener('click', function() {
        scale = Math.max(0.2, scale - 0.2);
        zoomImage.style.transform = `scale(${scale})`;
      });
      
      // 초기화 버튼
      modalElement.querySelector('.zoom-reset').addEventListener('click', function() {
        scale = 1;
        zoomImage.style.transform = `scale(${scale})`;
      });
      
      // 모달 닫힐 때 제거
      modalElement.addEventListener('hidden.bs.modal', function() {
        modalElement.remove();
      });
    });
  });
}

/**
 * 특수 항목 강조 표시 초기화
 */
function initializeSpecialItems() {
  // 특수 항목 버튼
  const specialButtons = document.querySelectorAll('[data-highlight-item]');
  
  specialButtons.forEach(button => {
    button.addEventListener('click', function() {
      const itemType = button.dataset.highlightItem;
      const pageId = button.dataset.page;
      const pageElement = document.getElementById(pageId);
      
      if (pageElement) {
        // 현재 강조 상태 토글
        const isActive = button.classList.contains('active');
        
        // 모든 강조 제거
        pageElement.querySelectorAll('.highlight-area').forEach(el => {
          el.classList.remove('highlight-area');
        });
        
        // 모든 버튼 비활성화
        pageElement.querySelectorAll('[data-highlight-item]').forEach(btn => {
          btn.classList.remove('active');
        });
        
        // 활성화되지 않은 경우에만 강조
        if (!isActive) {
          button.classList.add('active');
          
          // 항목 유형에 따라 다른 요소 강조
          if (itemType === 'stamps') {
            pageElement.querySelectorAll('.stamp-region').forEach(el => {
              el.classList.add('highlight-area');
            });
          } else if (itemType === 'handwriting') {
            pageElement.querySelectorAll('.handwriting-region').forEach(el => {
              el.classList.add('highlight-area');
            });
          } else if (itemType === 'strikethrough') {
            pageElement.querySelectorAll('.strikethrough-region').forEach(el => {
              el.classList.add('highlight-area');
            });
          } else if (itemType === 'tables') {
            pageElement.querySelectorAll('.table-region').forEach(el => {
              el.classList.add('highlight-area');
            });
          }
        }
      }
    });
  });
}

/**
 * 엔티티 필터링 기능
 */
function filterEntities(entityType) {
  const entityContainers = document.querySelectorAll('.entity-container');
  
  // 모든 컨테이너 숨기기
  entityContainers.forEach(container => {
    container.classList.add('d-none');
  });
  
  // 선택한 유형만 표시
  if (entityType === 'all') {
    entityContainers.forEach(container => {
      container.classList.remove('d-none');
    });
  } else {
    document.querySelectorAll(`.entity-container[data-entity-type="${entityType}"]`).forEach(container => {
      container.classList.remove('d-none');
    });
  }
  
  // 버튼 상태 업데이트
  document.querySelectorAll('.entity-filter-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelector(`.entity-filter-btn[data-entity-type="${entityType}"]`).classList.add('active');
}

/**
 * OCR 엔진 결과 비교 모달 표시
 */
function showEngineComparison(pageId) {
  const pageElement = document.getElementById(pageId);
  
  if (pageElement && pageElement.dataset.engineResults) {
    try {
      const engineResults = JSON.parse(pageElement.dataset.engineResults);
      
      // 모달 생성
      const modalElement = document.createElement('div');
      modalElement.className = 'modal fade';
      modalElement.id = 'engineModal';
      modalElement.setAttribute('tabindex', '-1');
      modalElement.setAttribute('aria-labelledby', 'engineModalLabel');
      modalElement.setAttribute('aria-hidden', 'true');
      
      // 엔진별 결과 HTML 생성
      let enginesHtml = '';
      for (const [engine, result] of Object.entries(engineResults)) {
        const confidence = (result.confidence * 100).toFixed(1);
        const confidenceClass = confidence > 90 ? 'success' : 
                               confidence > 70 ? 'primary' : 
                               confidence > 50 ? 'warning' : 'danger';
        
        enginesHtml += `
          <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
              <h6 class="mb-0">${engine}</h6>
              <span class="badge bg-${confidenceClass}">${confidence}%</span>
            </div>
            <div class="card-body">
              <p class="text-area">${result.text}</p>
            </div>
          </div>
        `;
      }
      
      // 모달 내용
      modalElement.innerHTML = `
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="engineModalLabel">OCR 엔진 결과 비교</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              ${enginesHtml}
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
            </div>
          </div>
        </div>
      `;
      
      // 모달 추가 및 표시
      document.body.appendChild(modalElement);
      const modal = new bootstrap.Modal(modalElement);
      modal.show();
      
      // 모달 닫힐 때 제거
      modalElement.addEventListener('hidden.bs.modal', function() {
        modalElement.remove();
      });
    } catch (error) {
      console.error('엔진 결과 파싱 오류:', error);
      showToast('엔진 결과를 불러올 수 없습니다.', 'danger');
    }
  } else {
    showToast('엔진 결과를 찾을 수 없습니다.', 'warning');
  }
}
