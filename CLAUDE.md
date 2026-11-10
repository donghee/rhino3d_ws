# rhino3d_ws 작업 규칙

## 시작 전
1. 작업할 프로젝트 폴더(`rhino3d_ws/<project>/`)에 `handoff.md`가 있으면 먼저 끝까지 읽고, 거기 적힌 현재 상태·다음 작업에서 이어서 진행한다.
   - 새 프로젝트면 `rhino3d_ws/<project>/` 폴더를 만들고 `handoff.md`도 그 안에 새로 만든다.
2. `rmcp.py call get_context`로 Rhino 문서 상태(객체 수, 선택, 뷰)를 확인한 뒤 작업한다.

## 환경
- Rhino 9 MCP: `http://norang.lan:10501/` (Rhino PC의 proxy → 127.0.0.1:10500). Claude Code MCP 이름은 `rhino`.
  - 연결이 안 되면 `python3 tools/rhino_remote.py start`로 Rhino PC에서 직접 다시 띄운다(아래 "Rhino PC 원격 제어" 참고).
- 같은 폴더의 두 경로: Linux `/home/donghee/mnt/norang/rhino3d_ws` = Rhino PC `D:/rhino3d_ws` (CIFS 공유 `//norang.lan/d`).
  - Rhino(MCP)에 넘기는 경로는 항상 Windows 경로(`D:/rhino3d_ws/...`)를 쓴다.
- `rhino` MCP 도구가 세션에 로드되지 않았으면 `python3 tools/rmcp.py`로 같은 서버를 JSON-RPC로 직접 호출한다.

## Rhino PC 원격 제어 (ssh norang.lan)
- Rhino PC(Windows)의 프로젝트 폴더는 `D:\rhino3d_ws` (Linux에서는 CIFS 마운트 `/home/donghee/mnt/norang/rhino3d_ws`).
- `ssh norang.lan`: 키 로그인, 사용자 `donghee`(관리자), 원격 셸은 Windows PowerShell 5.1이고 출력은 CP949.
  - cmd 문법(`&`, `%VAR%`)은 쓰지 않는다. PowerShell 스크립트를 `-EncodedCommand`로 보낸다(`tools/rhino_remote.py`의 `ps()` 참고).
  - X11 경고를 없애려면 `ssh -x`를 쓴다.
- SSH 세션(session 0)에서 Rhino나 `.bat`을 직접 실행하지 않는다. 화면에 보이지 않는 세션에서 떠서 쓸 수 없다.
  - GUI 프로그램은 로그인한 사용자의 데스크톱 세션(session 1)에서 실행되도록 예약 작업으로 띄운다: 대화형 로그온, 가장 높은 권한.
- 도구 `tools/rhino_remote.py`:
  ```
  python3 tools/rhino_remote.py status          # Rhino/proxy 프로세스, 10500/10501 포트, MCP 응답 여부
  python3 tools/rhino_remote.py start [--wait N] # tools/rhino3d_mcpstart.bat 실행 후 MCP 응답까지 대기 (기본 240초)
  python3 tools/rhino_remote.py stop            # tools/rhino3d_mcpstop.bat 실행 (Rhino 종료, 저장 질문은 Rhino PC 화면에서 답함)
  ```
  - 예약 작업 이름: `RhinoMCP-start`, `RhinoMCP-stop`. Rhino PC에 사용자가 로그인해 있어야 한다.
- MCP 요청이 빈 응답이거나 연결이 끊기면 먼저 `rhino_remote.py status`로 확인한다.
  - Rhino가 꺼져 있으면 `rhino_remote.py start`로 다시 띄운다.
  - 10500 포트는 Windows HTTP 서비스(PID 4)가 열고 있는 것이 정상이다.
- `stop`은 Rhino를 끈다. 저장하지 않은 모델이 있으면 먼저 `rmcp.py save`로 저장한다.
- `start` 후 Rhino 문서는 비어 있다. 이전 버전을 이어서 작업하려면 `open_doc`으로 `D:/rhino3d_ws/<project>/<project>_vNNN.3dm`을 연다.

## 모델링 스크립트 (run_python)
- 문서 핸들은 `__rhino_doc__`만 쓴다 (`scriptcontext.doc`, `rhinoscriptsyntax` 사용 금지).
- 스크립트 최상위 전역 이름이 함수 안에서 보이지 않는다 → 전체를 `def main():` 안에 넣고 import도 그 안에서 하고 마지막에 `main()` 호출.
- 셸 `echo`로 스크립트를 만들지 않는다(zsh가 `\r` 등을 변환). heredoc(`<<'EOF'`)으로 파일을 쓴다.
- `Brep.CreatePipe`의 가변 반지름은 실패할 수 있으니 일정 반지름으로 대체하는 fallback을 둔다.
- 모델 객체는 `<Project>::<부위>` 하위 레이어에 넣고, 레이어마다 색과 렌더 재질을 지정한다. 객체에 이름을 붙인다.
- 작업 후 `rmcp.py shot`으로 렌더 이미지를 찍어 직접 확인한다(필요하면 front/right 등 여러 뷰).

## 폴더 구조
```
rhino3d_ws/
  CLAUDE.md                                      # 공용 규칙
  tools/                                         # 공용 도구: rmcp.py, rhino_remote.py, stl2img.py,
                                                 #   rhino3d_mcpstart.bat / rhino3d_mcpstop.bat / rhino3d_mcp_proxy.py (Rhino PC에서 실행)
  <project>/                                     # 프로젝트마다 하나 (예: monkey/)
    handoff.md                                   # 이 프로젝트의 상태와 버전 내역
    <project>_v001.3dm / .jpg / .py
```
- `handoff.md`는 `rhino3d_ws` 바로 아래가 아니라 각 프로젝트 폴더 안에 둔다.

## 저장과 버전 관리
- 모델 버전은 git이 아니라 파일명으로 관리한다(아래). git은 백업·공유용: GitHub private 저장소 `rhino3d_ws`에 커밋·푸시한다. `*.stl`은 `.gitignore`로 제외한다(.3dm에서 다시 만들 수 있음).
- 모델은 해당 프로젝트 폴더 `<project>/`에만 저장한다. 다른 곳(Documents 등)에 저장하지 않는다.
- 파일명으로 버전을 관리한다: `<project>_v001.3dm`, `<project>_v002.3dm`, … (3자리 번호).
  - 같은 이름의 `.jpg`(미리보기)와 `.py`(그 버전을 만든 스크립트)를 함께 둔다.
  - 기존 버전 파일은 절대 덮어쓰거나 지우지 않는다. 변경하면 항상 다음 번호로 새로 저장한다.
- 저장 명령: `python3 tools/rmcp.py save <project> <script.py>` — 다음 번호를 자동으로 정해 .3dm/.jpg/.py를 저장한다.
- 저장할 때마다 `<project>/handoff.md`의 "모델 버전 내역" 표에 버전, 날짜, 변경 내용, 파일을 추가하고 "현재 상태"/"다음 작업"을 갱신한다.

## 도구: tools/rmcp.py
```
python3 tools/rmcp.py call <tool> '<json>'   # MCP 도구 호출 (예: get_context, list_objects, run_command)
python3 tools/rmcp.py run <script.py>        # Rhino에서 Python 실행
python3 tools/rmcp.py shot <out.jpg> [view] [mode]  # 전체 객체에 맞춘 뷰 캡처 (기본 perspective/Rendered)
python3 tools/rmcp.py save <project> [script.py]    # 다음 버전으로 저장
python3 tools/rmcp.py next <project>          # 다음 버전 이름 확인
python3 tools/rmcp.py preview <project> [N]   # Rhino 4면 캡처 → <project>/<project>_vNNN.png (최신 저장 버전, N을 주면 그 버전 이름)
python3 tools/rmcp.py stl <project>           # 열린 문서를 최신 저장 버전 이름으로 STL 내보내기 (덮어쓰기 안 함)
```
- 다른 도구: `tools/rhino_remote.py`(Rhino PC 원격 시작/종료), `tools/stl2img.py`(STL → PNG).

## Linux에서 미리보기
- STL 보기: `fstl <file>.stl` (가벼움, STL 전용, 창으로 열림).
- STL → 이미지: `python3 tools/stl2img.py <file>.stl [--view front|back|left|right|top|iso|all] [--size 900]`
  - f3d로 창 없이 렌더한다. 기본 출력은 STL 옆 `<name>_stl.png`(front), 다른 뷰는 `<name>_stl_<view>.png`. `all` = front + iso + right.
  - 뷰 방향은 Rhino의 Front/Right/Top 뷰와 같다(Z가 위, 모델 정면은 -Y).
- image-preview mod는 PNG/JPG 이미지만 보여준다.
- 사용자가 모델 "preview"를 요청하면 STL을 변환하지 않는다. Rhino에서 바로 4면을 캡처한다:
  1. `python3 tools/rmcp.py preview <project>`: Rhino에 열린 문서를 Top·Perspective·Front·Right 뷰로 캡처해 한 장의 PNG로 만든다. 이름은 최신 저장 버전과 같은 `<project>/<project>_vNNN.png`이고, 다시 실행하면 그 PNG만 새로 쓴다. 저장하지 않은 변경이 있으면 먼저 `rmcp.py save`로 새 버전을 만든 뒤 실행한다(저장 전에 실행하면 이전 버전 PNG를 덮어쓴다).
  2. image-preview 도구 `mcp__image-preview__preview`를 `file: "<project>/<project>_vNNN.png"`로 호출한다. 대화창 옆 Preview pane에 표시된다.
  - 터미널이 144칸보다 좁으면 도구로 연 pane은 그려지지 않는다. 그때는 사용자에게 `/preview <project>/<project>_vNNN.png`를 입력하라고 알린다.
- `stl2img.py`는 STL 파일 자체를 확인할 때만 쓴다.
