# 모듈 1 — OpenCR·다이나믹셀 P 제어 과제

## 장비·환경

- 라즈베리파이: Ubuntu 22.04.5 LTS (hostname `pa22`, aarch64). 상세 내용은 [results/환경확인.txt](results/환경확인.txt).
- 제어기: OpenCR 1.0
- 모터: 다이나믹셀 XM430-W350 (모델 1020), ID 12, Protocol 2.0, 1 Mbps, 1개
- 예제 코드: `opencr_position_p.ino` (Lv2 3강 P 제어 제공 예제)
- 펌웨어: 과제용 사전 빌드본 사용 (직접 컴파일하지 않음)

## 실행 방법

1. 라즈베리파이에 SSH로 접속한다. 업로드·시리얼 송수신·로그 저장은 모두 라즈베리파이에서 수행한다.
2. OpenCR을 USB로 연결하고 `/dev/ttyACM0` 인식을 확인한다.
3. 사전 빌드 펌웨어를 라즈베리파이에서 업로드한다 (기록: `results/upload.log`).
4. 시리얼로 `s <Kp> <speed_deg_s|max> <angle_deg>` 형식 명령을 보낸다. 이번 실행: `s 0.5 20 10` (Kp=0.5, 속도 상한 20°/s, 목표각 +10°).
5. 시작 위치를 0°로 보고 2초 후 목표가 반영된다. `x` 명령으로 언제든 즉시 정지한다.
6. 시리얼 출력을 타임스탬프와 함께 파일로 저장한다 (기록: `results/실행A.log`).

## 결과 파일 위치

| 파일 | 내용 |
|---|---|
| `results/환경확인.txt` | 라즈베리파이 hostname·OS·아키텍처·포트 |
| `results/upload.log` | 펌웨어 업로드 도구(opencr_ld) 출력 — 보드 인식, flash 쓰기, CRC 확인, 펌웨어 점프까지 |
| `results/실행A.log` | 실행 A 전체 기록 — 명령 전송부터 목표 변경 이후 측정값, 수동 정지 확인까지 |
