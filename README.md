# Computer Network Messenger Project

컴퓨터네트워크 Design Project: 복수 사용자 메신저 프로그램.

## 목표

- 로그인 서버는 현재 온라인 사용자의 `id`, `ip`, `port`를 파일에 저장한다.
- 사용자가 클라이언트를 실행하면 로그인 서버에 접속 정보를 등록한다.
- 클라이언트는 로그인 서버에서 온라인 사용자 목록을 받아 화면에 출력한다.
- 사용자 간 메시지는 로그인 서버를 거치지 않고 클라이언트끼리 직접 전송한다.
- 메시지 포맷은 HTTP처럼 헤더와 바디로 분리해 확장 가능하게 설계한다.

## 디렉터리 구조

```text
.
├── docs/                  # 설계 문서, 발표자료 초안
├── demo/                  # 시연 영상 URL HTML 등 제출 보조 파일
├── scripts/               # 실행 편의 스크립트
├── src/
│   └── messenger/
│       ├── client.py      # 사용자 프로그램, P2P 송수신
│       ├── login_server.py# 로그인 서버
│       ├── protocol.py    # 헤더/바디 메시지 포맷
│       ├── storage.py     # 온라인 사용자 목록 파일 저장
│       └── web_client.py  # 브라우저 UI용 로컬 클라이언트 서버
├── tests/                 # 단위 테스트
├── web/                   # 웹 UI 정적 파일
└── network_design.pdf     # 과제 설명 원본
```

## 실행 방법

로그인 서버:

```bash
PYTHONPATH=src python3 -m messenger.login_server --host 127.0.0.1 --port 9000
```

사용자 클라이언트:

```bash
PYTHONPATH=src python3 -m messenger.client --id alice --server-host 127.0.0.1 --server-port 9000 --listen-port 10001
PYTHONPATH=src python3 -m messenger.client --id bob --server-host 127.0.0.1 --server-port 9000 --listen-port 10002
```

웹 UI 클라이언트:

```bash
PYTHONPATH=src python3 -m messenger.web_client --id alice --server-host 127.0.0.1 --server-port 9000 --listen-port 10001 --web-port 8001
PYTHONPATH=src python3 -m messenger.web_client --id bob --server-host 127.0.0.1 --server-port 9000 --listen-port 10002 --web-port 8002
```

브라우저에서 Alice는 `http://127.0.0.1:8001`, Bob은 `http://127.0.0.1:8002`로 접속한다.

## 기본 명령

클라이언트 실행 후 사용할 수 있는 명령:

- `/users`: 온라인 사용자 목록 보기
- `/refresh`: 로그인 서버에서 온라인 사용자 목록 새로 받기
- `/invite <id>`: 메신저 세션에 사용자 초청
- `/send <message>`: 세션에 있는 모든 사용자에게 메시지 전송
- `/end`: 현재 메신저 세션 종료
- `/quit`: 로그아웃 후 프로그램 종료

## 제출물 체크리스트

- 팀명.pptx 또는 팀명.pdf
- 팀명.html: 5분 이내 YouTube 시연 영상 URL 포함
- 소스코드 파일 전체
- 최종 압축 파일명: 팀명.zip
