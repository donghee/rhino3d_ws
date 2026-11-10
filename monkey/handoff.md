# Handoff — monkey

작업 시작 전에 이 파일을 끝까지 읽고 이어서 진행한다. 작업이 끝나면 아래 "모델 버전 내역"과 "다음 작업"을 갱신한다.

## 현재 상태 (2026-11-11)

- Rhino 9 MCP 서버: `http://norang.lan:10501/` (Claude Code에 `rhino` 이름으로 user scope 등록됨)
- 프로젝트 폴더: Linux `/home/donghee/mnt/norang/rhino3d_ws/monkey` = Rhino PC `D:\rhino3d_ws\monkey`
- Rhino에 현재 열린 문서: monkey_v003 (객체 38개, `monkey_v003.3dm`을 연 상태)

## 모델 버전 내역

| 버전 | 날짜 | 변경 내용 | 파일 |
|---|---|---|---|
| v001 | 2026-11-10 | 최초 생성. 만화풍 원숭이: 머리, 눈 패치·주둥이, 눈(흰자·동공·하이라이트), 콧구멍, 미소, 눈썹, 귀(안쪽 포함), 몸통·배, 팔·손, 다리·발, 말린 꼬리. 객체 29개, 레이어 `Monkey::Fur/Skin/Eye/Pupil/Mouth`. 단위 그대로(높이 약 44). | `monkey_v001.{3dm,jpg,py,stl}` |
| v002 | 2026-11-11 | 눈썹 수정: 이마를 가로지르던 두꺼운 막대 눈썹 하나(찡그린 인상)를 좌우로 나뉜 얇은 아치형 눈썹 2개로 교체. 눈 위로 올려 머리 표면에 붙임(파이프, 반지름 0.42→0.3). 나머지는 v001과 같음. 객체 30개. | `monkey_v002.{3dm,jpg,py}`, 정면 얼굴 `monkey_v002_face.jpg` |
| v003 | 2026-11-11 | 꼬리로 나뭇가지에 거꾸로 매달린 자세. v002 몸을 Y축 기준 180° 뒤집음(x→-x, z→50-z, 얼굴은 계속 -Y). 팔은 머리 옆으로 늘어뜨림, 꼬리는 등에서 올라가 가지를 1바퀴 반 감음. 나무 추가: 줄기(x=-26), 가지(y=8, z≈60), 잎 6개, 레이어 `Tree::Bark/Leaves`. 객체 38개. | `monkey_v003.{3dm,jpg,py,png}` |

## 내보내기

- 2026-11-10 `monkey_v001.stl`: 바이너리 STL, 삼각형 509,476개, 25MB, 단위 mm(높이 약 44mm). 29개 객체를 각각 메시로 만들어 합치기만 함(불리언 합집합 안 함) → 부품끼리 겹친 상태. 3D 프린트용이면 합집합한 별도 버전 필요.
- 2026-11-11 `monkey_v001_stl.png`: STL을 f3d로 렌더한 정면 미리보기 (`f3d monkey_v001.stl --output monkey_v001_stl.png --resolution 900,900 --up +Z`).
- 2026-11-11 `monkey_v002.stl`: `rmcp.py stl monkey`로 내보냄. 바이너리 STL, 삼각형 500,500개, 25MB, 단위 mm. v001처럼 합집합 안 함.
- 2026-11-11 `monkey_v002_stl.png`, `_stl_iso.png`, `_stl_right.png`: `tools/stl2img.py monkey/monkey_v002.stl --view all`.
- 2026-11-11 `monkey_v002.png`: Rhino에서 직접 캡처한 4면(Top·Perspective·Front·Right) 미리보기 (`rmcp.py preview monkey`).
- 2026-11-11 `monkey_v003.png`: v003 4면 미리보기. (저장 전에 preview를 실행해 `monkey_v002.png`가 v003 내용으로 덮였던 것을 `monkey_v002.3dm`을 다시 열어 `rmcp.py preview monkey 2`로 복구함.)

## 다음 작업 / 메모

- monkey: v003(나무에 매달린 자세)까지 있음. STL은 v002까지. v003 다음 아이디어: 바닥/풀, 바나나 들기, 가지 흔들림 표현.
- 이전 테스트로 저장된 `C:\Users\donghee\Documents\monkey.3dm`는 v001과 같은 내용 (프로젝트 밖, 정리 대상).
