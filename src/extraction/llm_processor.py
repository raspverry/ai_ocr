"""
LLM 기반 데이터 추출 모듈
- 추출된 OCR 텍스트에서 구조화된 정보 추출
- OpenAI 또는 Anthropic API 활용
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
import openai
from anthropic import Anthropic
from src.core.config import config
from src.extraction.field_config import FieldConfig

# 로거 설정
logger = logging.getLogger(__name__)


class LLMProcessor:
    """LLM을 사용하여 OCR 텍스트에서 구조화된 데이터 추출"""
    
    def __init__(self):
        """초기화"""
        self.provider = config.get('extraction.llm.provider', 'openai')
        self.temperature = config.get('extraction.llm.temperature', 0.1)
        self.max_tokens = config.get('extraction.llm.max_tokens', 4000)
        
        # OpenAI 설정
        self.openai_api_key = config.get('extraction.llm.openai_api_key')
        self.openai_model = config.get('extraction.llm.openai_model', 'gpt-4')
        
        # Anthropic 설정
        self.anthropic_api_key = config.get('extraction.llm.anthropic_api_key')
        self.anthropic_model = config.get('extraction.llm.anthropic_model', 'claude-3-haiku-20240307')
        
        # 필드 설정 로드
        self.field_config = FieldConfig()
        
        # API 클라이언트 초기화
        self._init_clients()
    
    def _init_clients(self):
        """LLM API 클라이언트 초기화"""
        if self.provider == 'openai':
            if not self.openai_api_key:
                logger.warning("OpenAI API 키가 설정되지 않았습니다.")
                return
            
            openai.api_key = self.openai_api_key
            logger.info(f"OpenAI 클라이언트 초기화 (모델: {self.openai_model})")
        
        elif self.provider == 'anthropic':
            if not self.anthropic_api_key:
                logger.warning("Anthropic API 키가 설정되지 않았습니다.")
                return
            
            self.anthropic_client = Anthropic(api_key=self.anthropic_api_key)
            logger.info(f"Anthropic 클라이언트 초기화 (모델: {self.anthropic_model})")
    
    def extract_fields(self, 
                      ocr_text: str, 
                      fields: Optional[List[Dict[str, Any]]] = None, 
                      language: str = 'jpn') -> Dict[str, Any]:
        """
        OCR 텍스트에서 필드 추출
        
        Args:
            ocr_text: OCR로 추출된 텍스트
            fields: 추출할 필드 목록 (None이면 기본 필드 사용)
            language: 텍스트 언어 코드
        
        Returns:
            추출된 필드와 값
        """
        if not ocr_text:
            logger.warning("추출할 텍스트가 없습니다.")
            return {'fields': {}, 'error': '추출할 텍스트가 없습니다.'}
        
        # 필드 목록이 전달되지 않았으면 기본 필드 사용
        if fields is None:
            fields = self.field_config.get_fields()
        
        try:
            # 구체적인 필드 설명 및 컨텍스트 구성
            field_descriptions = self._prepare_field_descriptions(fields, language)
            
            # LLM에 전달할 프롬프트 구성
            prompt = self._build_prompt(ocr_text, field_descriptions, language)
            
            # LLM 호출
            response = self._call_llm(prompt)
            
            # 응답 파싱
            extracted_data = self._parse_response(response, fields)
            
            return {
                'fields': extracted_data,
                'raw_response': response
            }
        
        except Exception as e:
            logger.error(f"필드 추출 오류: {str(e)}")
            return {
                'fields': {},
                'error': f'필드 추출 오류: {str(e)}'
            }
    
    def _prepare_field_descriptions(self, 
                                  fields: List[Dict[str, Any]], 
                                  language: str) -> str:
        """
        추출할 필드의 상세 설명 구성
        
        Args:
            fields: 추출할 필드 목록
            language: 텍스트 언어 코드
        
        Returns:
            필드 설명 문자열
        """
        descriptions = []
        
        for i, field in enumerate(fields):
            field_name = field['name']
            field_type = field.get('type', 'text')
            context = field.get('context', '')
            regex = field.get('regex', '')
            
            # 필드 설명
            description = f"{i+1}. {field_name} (Type: {field_type})"
            
            # 컨텍스트 정보가 있으면 추가
            if context:
                # 컨텍스트가 '|'로 구분된 여러 키워드인 경우
                if '|' in context:
                    keywords = context.split('|')
                    context_info = ", ".join([f'"{k}"' for k in keywords])
                    description += f"\n   키워드: {context_info} 주변에서 값을 찾으세요."
                else:
                    description += f'\n   키워드: "{context}" 주변에서 값을 찾으세요.'
            
            # 정규식이 있으면 추가
            if regex:
                description += f'\n   패턴: 일반적인 형식은 "{regex}"와 같습니다.'
            
            # 필드 유형별 힌트
            if field_type == 'date':
                description += '\n   날짜 형식을 YYYY-MM-DD로 정규화하세요. 예: 2024-02-15'
            elif field_type == 'amount':
                description += '\n   금액에서 통화 기호와 쉼표를 제거하고 숫자만 반환하세요. 예: 1000.50'
            elif field_type == 'company':
                description += '\n   회사명에서 법적 형태(주식회사, LLC 등)를 포함하여 전체 이름을 추출하세요.'
            
            descriptions.append(description)
        
        return "\n\n".join(descriptions)
    
    def _build_prompt(self, 
                    ocr_text: str, 
                    field_descriptions: str, 
                    language: str) -> str:
        """
        LLM 프롬프트 구성
        
        Args:
            ocr_text: OCR로 추출된 텍스트
            field_descriptions: 필드 설명 문자열
            language: 텍스트 언어 코드
        
        Returns:
            LLM에 전달할 프롬프트
        """
        # 언어별 지시 조정
        language_instructions = {
            'jpn': "일본어 문서에서 다음 필드를 추출하세요.",
            'eng': "Extract the following fields from this English document.",
            'kor': "한국어 문서에서 다음 필드를 추출하세요.",
            'chi_sim': "从这份简体中文文档中提取以下字段。",
            'chi_tra': "從這份繁體中文文檔中提取以下字段。"
        }
        
        instruction = language_instructions.get(language, language_instructions['eng'])
        
        # 프롬프트 구성
        prompt = f"""# 문서 필드 추출

{instruction}

## 추출할 필드
{field_descriptions}

## 추출 규칙
1. 존재하지 않거나 확인할 수 없는 필드는 null로 반환하세요.
2. 값이 있으면 정확히 추출하되, 필요 시 정규화하세요.
3. 주변 문맥을 고려하여 가장 관련성 높은 값을 선택하세요.
4. 여러 비슷한 값이 있으면, 문서 문맥에 가장 적합한 것을 선택하세요.
5. 응답은 JSON 형식으로 제공하세요.

## OCR로 추출된 텍스트
```
{ocr_text}
```

## 응답 형식
다음과 같은, 필드 이름과 해당 값으로 이루어진 JSON 형식으로 응답하세요:
```json
{
  "필드1": "값1",
  "필드2": "값2",
  ...
}
```
JSON만 반환하고 다른 설명은 포함하지 마세요."""

        return prompt
    
    def _call_llm(self, prompt: str) -> str:
        """
        LLM API 호출
        
        Args:
            prompt: LLM에 전달할 프롬프트
        
        Returns:
            LLM 응답 텍스트
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if self.provider == 'openai':
                    return self._call_openai(prompt)
                elif self.provider == 'anthropic':
                    return self._call_anthropic(prompt)
                else:
                    raise ValueError(f"지원하지 않는 LLM 제공자: {self.provider}")
            
            except Exception as e:
                logger.warning(f"LLM API 호출 오류 (시도 {attempt+1}/{max_retries}): {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                else:
                    raise
    
    def _call_openai(self, prompt: str) -> str:
        """
        OpenAI API 호출
        
        Args:
            prompt: LLM에 전달할 프롬프트
        
        Returns:
            LLM 응답 텍스트
        """
        response = openai.ChatCompletion.create(
            model=self.openai_model,
            messages=[
                {"role": "system", "content": "You are a document extraction specialist that always responds in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_anthropic(self, prompt: str) -> str:
        """
        Anthropic API 호출
        
        Args:
            prompt: LLM에 전달할 프롬프트
        
        Returns:
            LLM 응답 텍스트
        """
        response = self.anthropic_client.messages.create(
            model=self.anthropic_model,
            system="You are a document extraction specialist that always responds in valid JSON format.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.content[0].text.strip()
    
    def _parse_response(self, 
                       response: str, 
                       fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        LLM 응답 파싱
        
        Args:
            response: LLM 응답 텍스트
            fields: 추출할 필드 목록
        
        Returns:
            추출된 필드와 값
        """
        # JSON 코드 블록 추출 (```json ... ``` 형식인 경우)
        if "```json" in response and "```" in response.split("```json", 1)[1]:
            json_part = response.split("```json", 1)[1].split("```", 1)[0].strip()
        # JSON 코드 블록 추출 (``` ... ``` 형식인 경우)
        elif "```" in response and "```" in response.split("```", 1)[1]:
            json_part = response.split("```", 1)[1].split("```", 1)[0].strip()
        else:
            json_part = response.strip()
        
        try:
            extracted_data = json.loads(json_part)
            
            # 필드 유형에 따른 후처리
            processed_data = {}
            
            for field in fields:
                field_name = field['name']
                field_type = field.get('type', 'text')
                
                # 필드 값 가져오기
                value = extracted_data.get(field_name)
                
                # null, None, "null" 등을 None으로 정규화
                if value is None or value == "null" or (isinstance(value, str) and value.lower() == "null"):
                    processed_data[field_name] = None
                    continue
                
                # 필드 유형별 후처리
                if field_type == 'date' and value:
                    # 날짜 정규화 (추가 정규화 로직 구현 가능)
                    processed_data[field_name] = value
                
                elif field_type == 'amount' and value:
                    # 숫자만 유지
                    if isinstance(value, str):
                        import re
                        value = re.sub(r'[^\d.]', '', value)
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    processed_data[field_name] = value
                
                else:
                    processed_data[field_name] = value
            
            return processed_data
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {str(e)}, 응답: {response}")
            return {}
