#!/bin/bash
# 초고정밀 OCR 시스템 의존성 설치 스크립트
# 실행: bash scripts/install_dependencies.sh

set -e

echo "=== 초고정밀 OCR 시스템 의존성 설치 스크립트 ==="
echo "플랫폼: $(uname -s)"

# 사용자 권한 확인
if [ "$(uname -s)" = "Linux" ] && [ "$EUID" -ne 0 ]; then
  echo "경고: 시스템 패키지 설치를 위해 관리자 권한이 필요합니다."
  echo "Root 권한으로 실행하려면: sudo bash $0"
  read -p "계속 진행하시겠습니까? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Python 버전 확인
python_version=$(python3 --version 2>&1 | cut -d ' ' -f 2)
echo "Python 버전: $python_version"

# Python 최소 버전 확인
python_major=$(echo $python_version | cut -d '.' -f 1)
python_minor=$(echo $python_version | cut -d '.' -f 2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 8 ]); then
  echo "오류: Python 3.8 이상이 필요합니다."
  exit 1
fi

# 운영체제 감지
if [ "$(uname -s)" = "Linux" ]; then
  # Linux 의존성 설치
  if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    echo "=== Debian/Ubuntu 시스템 패키지 설치 ==="
    sudo apt-get update
    sudo apt-get install -y \
      build-essential \
      libpq-dev \
      tesseract-ocr \
      libtesseract-dev \
      tesseract-ocr-jpn \
      tesseract-ocr-kor \
      tesseract-ocr-chi-sim \
      tesseract-ocr-chi-tra \
      libleptonica-dev \
      pkg-config \
      mecab \
      libmecab-dev \
      mecab-ipadic-utf8 \
      unzip \
      wget \
      curl \
      git \
      redis-server \
      poppler-utils
  
  elif [ -f /etc/redhat-release ]; then
    # CentOS/RHEL/Fedora
    echo "=== CentOS/RHEL/Fedora 시스템 패키지 설치 ==="
    sudo dnf install -y \
      gcc \
      gcc-c++ \
      make \
      postgresql-devel \
      tesseract \
      tesseract-devel \
      tesseract-langpack-jpn \
      tesseract-langpack-kor \
      tesseract-langpack-chi_sim \
      tesseract-langpack-chi_tra \
      mecab \
      mecab-devel \
      unzip \
      wget \
      curl \
      git \
      redis \
      poppler-utils
  fi
  
  # MeCab 일본어 사전 설치
  echo "=== MeCab 일본어 NEologd 사전 설치 ==="
  git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git /tmp/mecab-ipadic-neologd
  cd /tmp/mecab-ipadic-neologd
  ./bin/install-mecab-ipadic-neologd -n -y
  cd -
  rm -rf /tmp/mecab-ipadic-neologd

elif [ "$(uname -s)" = "Darwin" ]; then
  # macOS 의존성 설치
  echo "=== macOS 시스템 패키지 설치 ==="
  
  # Homebrew 확인
  if ! command -v brew &> /dev/null; then
    echo "Homebrew가 설치되어 있지 않습니다. Homebrew를 먼저 설치해주세요."
    echo "설치 명령어: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
  fi
  
  brew install \
    tesseract \
    tesseract-lang \
    mecab \
    mecab-ipadic \
    redis \
    poppler
  
  # MeCab 일본어 사전 설치
  echo "=== MeCab 일본어 NEologd 사전 설치 ==="
  git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git /tmp/mecab-ipadic-neologd
  cd /tmp/mecab-ipadic-neologd
  ./bin/install-mecab-ipadic-neologd -n -y
  cd -
  rm -rf /tmp/mecab-ipadic-neologd

elif [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]]; then
  # Windows (Git Bash/MSYS2)
  echo "=== Windows 시스템 패키지 설치 ==="
  echo "Windows에서는 시스템 패키지를 자동으로 설치할 수 없습니다."
  echo "다음 패키지를 수동으로 설치해주세요:"
  echo "1. Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki"
  echo "2. Redis: https://github.com/microsoftarchive/redis/releases"
  echo "3. MeCab: https://taku910.github.io/mecab/#download"
  echo "4. Poppler (PDF 처리용): http://blog.alivate.com.au/poppler-windows/"
  
  read -p "패키지를 설치하셨나요? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "시스템 패키지를 설치한 후 다시 시도해주세요."
    exit 1
  fi
fi

# Python 가상 환경 생성 (선택 사항)
if [ ! -d "venv" ]; then
  echo "=== Python 가상 환경 생성 ==="
  python3 -m venv venv
  echo "가상 환경이 생성되었습니다."
  echo "가상 환경을 활성화하려면: source venv/bin/activate (Linux/macOS) 또는 venv\\Scripts\\activate (Windows)"
  
  read -p "가상 환경을 활성화할까요? (y/n): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ "$(uname -s)" = "Linux" ] || [ "$(uname -s)" = "Darwin" ]; then
      source venv/bin/activate
    elif [[ "$(uname -s)" == MINGW* ]] || [[ "$(uname -s)" == MSYS* ]]; then
      source venv/Scripts/activate
    fi
    echo "가상 환경이 활성화되었습니다."
  fi
fi

# Python 패키지 설치
echo "=== Python 패키지 설치 ==="
pip install --upgrade pip
pip install -r requirements.txt

# OCR 모델 다운로드
echo "=== OCR 모델 다운로드 ==="
python -m scripts.download_models

# 디렉토리 생성
echo "=== 디렉토리 구조 생성 ==="
mkdir -p storage configs/fields models/tessdata logs

# 설치 완료
echo "=== 설치 완료 ==="
echo "초고정밀 OCR 시스템 의존성 설치가 완료되었습니다."
echo "시스템을 시작하려면: python main.py"
echo "작업자를 시작하려면: python -m src.worker.start"
