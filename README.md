# TUI-K6-Runner

<img width="1102" height="618" alt="image" src="https://github.com/user-attachments/assets/c4d43c8a-66bf-4ee4-aac3-feb11462fb2d" />

<img width="1118" height="677" alt="image" src="https://github.com/user-attachments/assets/3cef3d48-81fd-4fc7-83ee-445371efc5dc" />

<img width="1118" height="682" alt="image" src="https://github.com/user-attachments/assets/e05ea0ed-60fe-4cd5-bc42-3d5e529745af" />

## How to use

- install Python 3.11 (supported version is fixed to 3.11.x)
- install K6
- install project dependencies:

  ```bash
  pip install -r requirements.txt
  ```

- run app using the only supported entrypoint:

  ```bash
  python main.py
  ```

## Architecture note

The launch bootstrap is now in `main.py` only. The main UI and application behavior live in:

- `app.py` — `K6TestApp` composition and app initialization
- `app_mixins/` — UI/event/request/stage behavior split by responsibility
- `k6/` — k6 run state, process control, parsing and service/presenter logic

Please make future UI changes in these modules, not in legacy monolithic entrypoint implementations.
