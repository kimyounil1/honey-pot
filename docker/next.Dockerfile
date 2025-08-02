# Node.js 20 LTS
FROM node:20-slim

# 컨테이너 작업 디렉토리
WORKDIR /app

# 패키지 정보 복사 후 설치 (이미지 빌드 시 캐시 활용)
COPY package*.json ./
CMD ["rm", "-rf", "node_modules", "package-lock.json"]

# node_modules 설치 (개발 환경용)
RUN npm install

# 나머지 소스코드 복사 (실제 dev 단계에서는 볼륨으로 덮어씀)
COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
