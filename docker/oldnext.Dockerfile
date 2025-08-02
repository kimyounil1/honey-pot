# Node.js 20 경량 이미지 사용
FROM node:20-alpine

# 컨테이너 내부 작업 디렉토리
WORKDIR /next-js

# package.json만 먼저 복사 (캐시 활용)
# COPY package*.json ./

# 의존성 설치
# RUN npm install

# 소스 복사
COPY . .

# Next.js 개발 서버 포트
EXPOSE 3000

# 개발 모드 실행
CMD ["npm", "run", "dev"]
