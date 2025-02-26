"""
OCR 텍스트 후처리 모듈
- 언어별 텍스트 정규화
- 일본어 특화 텍스트 보정
- 비즈니스 문서 양식 정규화
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
import unicodedata

# 로거 설정
logger = logging.getLogger(__name__)

# 선택적 라이브러리 임포트
try:
    import jaconv  # 일본어 문자 변환
except ImportError:
    jaconv = None
    logger.warning("jaconv 라이브러리가 설치되지 않았습니다. 일본어 변환 기능이 제한됩니다.")

try:
    import fugashi  # 일본어 형태소 분석
except ImportError:
    fugashi = None
    logger.warning("fugashi 라이브러리가 설치되지 않았습니다. 일본어 형태소 분석 기능이 제한됩니다.")

try:
    import MeCab  # 한국어/일본어 형태소 분석
except ImportError:
    MeCab = None
    logger.warning("MeCab 라이브러리가 설치되지 않았습니다. 형태소 분석 기능이 제한됩니다.")

try:
    import nltk  # 자연어 처리
    nltk.download('punkt', quiet=True)
except ImportError:
    nltk = None
    logger.warning("NLTK 라이브러리가 설치되지 않았습니다. 텍스트 분석 기능이 제한됩니다.")


class PostProcessor:
    """OCR 텍스트 후처리 클래스"""
    
    def __init__(self):
        """초기화"""
        # 형태소 분석기 초기화
        self.tokenizers = {}
        self._initialize_tokenizers()
        
        # 비즈니스 문서 패턴
        self.business_patterns = {
            'jpn': {
                'date': [
                    # 일본식 날짜 패턴 (2023年1月1日 → 2023年01月01日)
                    (r'(\d{4})年(\d{1})月(\d{1})日', r'\1年0\2月0\3日'),  # 2023年1月1日
                    (r'(\d{4})年(\d{2})月(\d{1})日', r'\1年\2月0\3日'),   # 2023年01月1日
                    (r'(\d{4})年(\d{1})月(\d{2})日', r'\1年0\2月\3日'),   # 2023年1月01日
                    
                    # 令和/平成/昭和 연호
                    (r'(令和|平成|昭和)(\d{1})年(\d{1})月(\d{1})日', r'\1\2年0\3月0\4日'),
                    (r'(令和|平成|昭和)(\d{2})年(\d{1})月(\d{1})日', r'\1\2年0\3月0\4日')
                ],
                'amount': [
                    # 일본식 금액 정규화 (¥1000 → ¥1,000)
                    (r'¥\s*(\d{4,})', lambda m: f"¥{int(m.group(1)):,}"),
                    (r'(\d{4,})\s*円', lambda m: f"{int(m.group(1)):,}円")
                ],
                'company': [
                    # 회사명 패턴 정규화
                    (r'株式含社', r'株式会社'),
                    (r'株式会杜', r'株式会社'),
                    (r'株式會社', r'株式会社'),
                    (r'有恨会社', r'有限会社'),
                    (r'含同会社', r'合同会社')
                ],
                'postcode': [
                    # 우편번호 패턴 정규화
                    (r'〒\s*(\d{3})\s*[-−]\s*(\d{4})', r'〒\1-\2')
                ]
            },
            'kor': {
                'date': [
                    # 한국식 날짜 패턴 정규화
                    (r'(\d{4})년\s*(\d{1})월\s*(\d{1})일', r'\1년 0\2월 0\3일'),
                    (r'(\d{4})년\s*(\d{2})월\s*(\d{1})일', r'\1년 \2월 0\3일'),
                    (r'(\d{4})년\s*(\d{1})월\s*(\d{2})일', r'\1년 0\2월 \3일'),
                    
                    # 표준 날짜 형식
                    (r'(\d{4})[./-](\d{1})[./-](\d{1})', r'\1-0\2-0\3'),
                    (r'(\d{4})[./-](\d{2})[./-](\d{1})', r'\1-\2-0\3'),
                    (r'(\d{4})[./-](\d{1})[./-](\d{2})', r'\1-0\2-\3')
                ],
                'amount': [
                    # 한국식 금액 정규화
                    (r'₩\s*(\d{4,})', lambda m: f"₩{int(m.group(1)):,}"),
                    (r'(\d{4,})\s*원', lambda m: f"{int(m.group(1)):,}원")
                ],
                'company': [
                    # 회사명 패턴 정규화
                    (r'(주)\s*식\s*회\s*사', r'(주)'),
                    (r'주\s*식\s*회\s*사', r'주식회사')
                ],
                'registration': [
                    # 사업자등록번호 패턴 정규화
                    (r'(\d{3})\s*[-−]?\s*(\d{2})\s*[-−]?\s*(\d{5})', r'\1-\2-\3')
                ]
            },
            'eng': {
                'date': [
                    # 영어 날짜 패턴 정규화
                    (r'(\w{3})\s+(\d{1}),\s+(\d{4})', r'\1 0\2, \3'),  # Jan 1, 2023
                    (r'(\d{1})/(\d{1})/(\d{4})', r'0\1/0\2/\3'),       # 1/1/2023
                    (r'(\d{1})/(\d{2})/(\d{4})', r'0\1/\2/\3'),        # 1/01/2023
                    (r'(\d{2})/(\d{1})/(\d{4})', r'\1/0\2/\3')         # 01/1/2023
                ],
                'amount': [
                    # 영어 금액 정규화
                    (r'\$\s*(\d{4,})', lambda m: f"${int(m.group(1)):,}"),
                    (r'(\d{4,})\s*USD', lambda m: f"{int(m.group(1)):,} USD")
                ],
                'company': [
                    # 회사명 패턴 정규화
                    (r'Inc\b\.?', r'Inc.'),
                    (r'Corp\b\.?', r'Corp.'),
                    (r'Ltd\b\.?', r'Ltd.'),
                    (r'LLC\b\.?', r'LLC'),
                    (r'LLP\b\.?', r'LLP')
                ]
            }
        }
        
        # 공통 정규화 패턴
        self.common_patterns = {
            'whitespace': [
                # 공백 정규화
                (r'\s+', ' '),                      # 여러 공백을 하나로
                (r'^\s+|\s+$', '')                  # 앞뒤 공백 제거
            ],
            'linebreak': [
                # 줄바꿈 정규화
                (r'\n\s*\n+', '\n\n'),             # 여러 빈 줄을 하나로
                (r'^\n+|\n+$', '')                  # 앞뒤 줄바꿈 제거
            ],
            'email': [
                # 이메일 형식 정규화
                (r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+)\.([a-zA-Z0-9-.]+)', 
                 lambda m: f"{m.group(1)}@{m.group(2)}.{m.group(3).lower()}")
            ]
        }
        
        # 언어별 단어/문장 토큰화 패턴
        self.sentence_patterns = {
            'jpn': r'(?<=[。．！？])',
            'kor': r'(?<=[.!?])',
            'eng': r'(?<=[.!?])\s',
            'chi_sim': r'(?<=[。！？])',
            'chi_tra': r'(?<=[。！？])'
        }
    
    def _initialize_tokenizers(self):
        """언어별 토큰화기 초기화"""
        # 일본어 토큰화기
        if fugashi is not None:
            try:
                self.tokenizers["jpn"] = fugashi.Tagger("-Owakati")
                logger.info("일본어 토큰화기(Fugashi) 초기화 성공")
            except Exception as e:
                logger.error(f"일본어 토큰화기 초기화 오류: {e}")
        
        # 한국어 토큰화기
        if MeCab is not None:
            try:
                self.tokenizers["kor"] = MeCab.Tagger("-d /usr/local/lib/mecab/dic/mecab-ko-dic")
                logger.info("한국어 토큰화기(MeCab) 초기화 성공")
            except Exception as e:
                try:
                    # 대체 경로 시도
                    self.tokenizers["kor"] = MeCab.Tagger()
                    logger.info("한국어 토큰화기(MeCab) 초기화 성공 (기본 경로)")
                except Exception as e2:
                    logger.error(f"한국어 토큰화기 초기화 오류: {e2}")
    
    def process(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        OCR 결과 텍스트 후처리
        
        Args:
            ocr_result: OCR 인식 결과 딕셔너리
        
        Returns:
            후처리된 OCR 결과
        """
        if not ocr_result or "text" not in ocr_result or not ocr_result["text"]:
            return ocr_result
        
        # 결과 복사
        result = ocr_result.copy()
        text = result["text"]
        lang = result.get("language", "eng")
        
        # 공통 텍스트 정규화
        text = self._normalize_common(text)
        
        # 언어별 텍스트 정규화
        if lang == "jpn":
            text = self._process_japanese(text)
        elif lang == "kor":
            text = self._process_korean(text)
        elif lang == "eng":
            text = self._process_english(text)
        elif lang in ["chi_sim", "chi_tra"]:
            text = self._process_chinese(text, lang)
        
        # 비즈니스 문서 형식 정규화
        text = self._format_business_document(text, lang)
        
        # 결과 업데이트
        result["text"] = text
        
        # 페이지별 처리 (있는 경우)
        if "pages" in result and isinstance(result["pages"], list):
            for i, page in enumerate(result["pages"]):
                if "text" in page and page["text"]:
                    page_text = page["text"]
                    
                    # 공통 텍스트 정규화
                    page_text = self._normalize_common(page_text)
                    
                    # 언어별 텍스트 정규화
                    if lang == "jpn":
                        page_text = self._process_japanese(page_text)
                    elif lang == "kor":
                        page_text = self._process_korean(page_text)
                    elif lang == "eng":
                        page_text = self._process_english(page_text)
                    elif lang in ["chi_sim", "chi_tra"]:
                        page_text = self._process_chinese(page_text, lang)
                    
                    # 비즈니스 문서 형식 정규화
                    page_text = self._format_business_document(page_text, lang)
                    
                    # 결과 업데이트
                    result["pages"][i]["text"] = page_text
        
        return result
    
    def _normalize_common(self, text: str) -> str:
        """
        공통 텍스트 정규화
        
        Args:
            text: 원본 텍스트
        
        Returns:
            정규화된 텍스트
        """
        if not text:
            return ""
        
        # 유니코드 정규화 (NFKC)
        text = unicodedata.normalize('NFKC', text)
        
        # 공통 패턴 적용
        for pattern_type, patterns in self.common_patterns.items():
            for pattern, replacement in patterns:
                text = re.sub(pattern, replacement, text)
        
        return text
    
    def _process_japanese(self, text: str) -> str:
        """
        일본어 텍스트 처리
        
        Args:
            text: 원본 텍스트
        
        Returns:
            처리된 텍스트
        """
        if not text:
            return ""
        
        # jaconv 사용 가능한 경우 전각/반각 변환
        if jaconv is not None:
            text = jaconv.normalize(text)
        
        # 특수 기호 정규화
        text = re.sub(r'[﹅﹆]', '・', text)  # 중점 정규화
        
        # 일본어 숫자 정규화 (전각 → 반각)
        text = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
        
        # 일본어 형태소 분석 (토큰화)
        if "jpn" in self.tokenizers:
            try:
                tokenized = self.tokenizers["jpn"].parse(text)
                text = tokenized.strip()
            except Exception as e:
                logger.warning(f"일본어 토큰화 오류: {e}")
        
        # 줄바꿈 정규화
        text = re.sub(r'(?<=[。．！？])\s*(?=\S)', '\n', text)
        
        return text
    
    def _process_korean(self, text: str) -> str:
        """
        한국어 텍스트 처리
        
        Args:
            text: 원본 텍스트
        
        Returns:
            처리된 텍스트
        """
        if not text:
            return ""
        
        # 한국어 숫자 정규화 (전각 → 반각)
        text = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
        
        # 한국어 조사 정규화
        text = re.sub(r'([가-힣])\s+(을|를|이|가|은|는|의|에|로|으로|에서|도|만)', r'\1\2', text)
        
        # 줄바꿈 정규화
        text = re.sub(r'(?<=[.!?])\s*(?=\S)', '\n', text)
        
        return text
    
    def _process_english(self, text: str) -> str:
        """
        영어 텍스트 처리
        
        Args:
            text: 원본 텍스트
        
        Returns:
            처리된 텍스트
        """
        if not text:
            return ""
        
        # 문장 시작 대문자화
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s[0].upper() + s[1:] if s and len(s) > 0 else s for s in sentences]
        text = ' '.join(sentences)
        
        # 일반적인 영어 비즈니스 용어 교정
        business_terms = {
            "Ud.": "Ltd.",
            "Ine.": "Inc.",
            "Ilc": "LLC",
            "Lld.": "Ltd.",
            "limiled": "limited",
            "corporalion": "corporation"
        }
        
        for wrong, correct in business_terms.items():
            text = re.sub(fr'\b{wrong}\b', correct, text)
        
        return text
    
    def _process_chinese(self, text: str, lang: str = "chi_sim") -> str:
        """
        중국어 텍스트 처리
        
        Args:
            text: 원본 텍스트
            lang: 언어 코드 (chi_sim: 간체, chi_tra: 번체)
        
        Returns:
            처리된 텍스트
        """
        if not text:
            return ""
        
        # 중국어 숫자 정규화 (전각 → 반각)
        text = re.sub(r'[０-９]', lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
        
        # 특수 기호 정규화
        text = re.sub(r'[﹅﹆]', '・', text)
        
        # 중국어 구두점 정규화
        text = re.sub(r'。\s*', '。\n', text)
        
        return text
    
    def _format_business_document(self, text: str, lang: str) -> str:
        """
        비즈니스 문서 형식 정규화
        
        Args:
            text: 원본 텍스트
            lang: 언어 코드
        
        Returns:
            정규화된 텍스트
        """
        if not text:
            return ""
        
        # 언어별 비즈니스 패턴 적용
        if lang in self.business_patterns:
            for pattern_type, patterns in self.business_patterns[lang].items():
                for pattern, replacement in patterns:
                    text = re.sub(pattern, replacement, text)
        
        return text
    
    def split_into_sentences(self, text: str, lang: str = "eng") -> List[str]:
        """
        텍스트를 문장 단위로 분리
        
        Args:
            text: 원본 텍스트
            lang: 언어 코드
        
        Returns:
            문장 목록
        """
        if not text:
            return []
        
        # 언어별 문장 분리 패턴
        pattern = self.sentence_patterns.get(lang, self.sentence_patterns["eng"])
        
        # nltk 사용 가능한 경우 (영어)
        if lang == "eng" and nltk is not None:
            try:
                return nltk.sent_tokenize(text)
            except:
                # 패턴 기반 분리로 대체
                pass
        
        # 패턴 기반 문장 분리
        return re.split(pattern, text)
    
    def extract_business_entities(self, text: str, lang: str = "eng") -> Dict[str, List[str]]:
        """
        비즈니스 관련 엔티티 추출
        
        Args:
            text: 원본 텍스트
            lang: 언어 코드
        
        Returns:
            추출된 엔티티 (회사명, 날짜, 금액 등)
        """
        entities = {
            'companies': [],
            'dates': [],
            'amounts': [],
            'persons': [],
            'addresses': [],
            'emails': [],
            'phones': []
        }
        
        if not text:
            return entities
        
        # 이메일 추출 (공통)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        entities['emails'] = re.findall(email_pattern, text)
        
        # 전화번호 추출 (공통)
        phone_patterns = [
            r'\+\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,4}',  # 국제 형식
            r'\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}'                        # 국내 형식
        ]
        for pattern in phone_patterns:
            entities['phones'].extend(re.findall(pattern, text))
        
        # 언어별 엔티티 추출
        if lang == "jpn":
            # 일본어 회사명 (주식회사, 유한회사 등)
            company_patterns = [
                r'株式会社[\s]?([^\s・（()]{1,20})',
                r'合同会社[\s]?([^\s・（()]{1,20})',
                r'有限会社[\s]?([^\s・（()]{1,20})'
            ]
            for pattern in company_patterns:
                for match in re.finditer(pattern, text):
                    if match.group(0) not in entities['companies']:
                        entities['companies'].append(match.group(0))
            
            # 일본식 날짜
            date_patterns = [
                r'(令和|平成|昭和)?\s*(\d{1,2})?\s*年\s*(\d{1,2})?\s*月\s*(\d{1,2})?\s*日',
                r'\d{4}年\d{1,2}月\d{1,2}日',
                r'\d{4}/\d{1,2}/\d{1,2}'
            ]
            for pattern in date_patterns:
                entities['dates'].extend(re.findall(pattern, text))
            
            # 일본식 금액
            amount_patterns = [
                r'¥\s*(\d{1,3}(,\d{3})*(\.\d+)?)',
                r'(\d{1,3}(,\d{3})*(\.\d+)?)\s*円'
            ]
            for pattern in amount_patterns:
                entities['amounts'].extend(re.findall(pattern, text))
            
            # 주소 (일본 우편번호 포함)
            address_patterns = [
                r'〒\d{3}-\d{4}',
                r'[東西南北]?京都?[府県]'
            ]
            for pattern in address_patterns:
                for match in re.finditer(pattern, text):
                    # 주변 문맥 추출
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 30)
                    entities['addresses'].append(text[start:end])
        
        elif lang == "kor":
            # 한국 회사명
            company_patterns = [
                r'(주)\s*식\s*회\s*사\s*([^\s]{1,20})',
                r'([^\s]{1,20})\s*(주)\s*식\s*회\s*사',
                r'([^\s]{1,20})\s*주식회사'
            ]
            for pattern in company_patterns:
                entities['companies'].extend(re.findall(pattern, text))
            
            # 한국식 날짜
            date_patterns = [
                r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
                r'\d{4}[-\.]\d{1,2}[-\.]\d{1,2}'
            ]
            for pattern in date_patterns:
                entities['dates'].extend(re.findall(pattern, text))
            
            # 한국식 금액
            amount_patterns = [
                r'₩\s*(\d{1,3}(,\d{3})*(\.\d+)?)',
                r'(\d{1,3}(,\d{3})*(\.\d+)?)\s*원'
            ]
            for pattern in amount_patterns:
                entities['amounts'].extend(re.findall(pattern, text))
        
        elif lang == "eng":
            # 영어 회사명
            company_patterns = [
                r'([A-Z][a-zA-Z0-9\s,]{2,30})\s+(Inc|Corp|LLC|Ltd|LLP|Limited|Corporation)\.?',
                r'([A-Z][a-zA-Z0-9\s,]{2,30})\s+Company'
            ]
            for pattern in company_patterns:
                entities['companies'].extend(re.findall(pattern, text))
            
            # 영어 날짜
            date_patterns = [
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},\s+\d{4}',
                r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}',
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{4}-\d{1,2}-\d{1,2}'
            ]
            for pattern in date_patterns:
                entities['dates'].extend(re.findall(pattern, text))
            
            # 영어 금액
            amount_patterns = [
                r'\$\s*(\d{1,3}(,\d{3})*(\.\d+)?)',
                r'USD\s*(\d{1,3}(,\d{3})*(\.\d+)?)'
            ]
            for pattern in amount_patterns:
                entities['amounts'].extend(re.findall(pattern, text))
        
        # 중복 제거
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
