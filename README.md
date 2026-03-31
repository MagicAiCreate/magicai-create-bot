python3 - <<'PY'
from pathlib import Path

p = Path('/root/bot.py')
text = p.read_text(encoding='utf-8')

old = '''def submit_kling_task(task):
    mode = task.get("mode", "text")
    prompt = task.get("prompt", "")
    size = task.get("size", "9:16")
    duration = task.get("duration", 5)
    photo_file_id = task.get("photo_file_id", "")
    ref_file_id = task.get("ref_file_id", "")

    return {
        "ok": False,
        "mode": mode,
        "prompt": prompt,
        "size": size,
        "duration": duration,
        "photo_file_id": photo_file_id,
        "ref_file_id": ref_file_id,
        "reason": "KLING_STAGE1_NOT_ENABLED"
    }


'''

new = '''def submit_kling_task(task):
    mode = task.get("mode", "text")
    prompt = task.get("prompt", "")
    size = task.get("size", "9:16")
    duration = task.get("duration", 5)
    photo_file_id = task.get("photo_file_id", "")
    ref_file_id = task.get("ref_file_id", "")
    task_id_local = task.get("task_id", "")

    if mode != "text":
        return {
            "ok": False,
            "reason": f"KLING_NOT_ENABLED_FOR_MODE_{mode}"
        }

    payload = {
        "model_name": "kling-v2-6",
        "prompt": prompt,
        "duration": str(duration),
        "mode": "std",
        "sound": "off",
        "aspect_ratio": str(size),
        "external_task_id": str(task_id_local)
    }

    try:
        r = requests.post(
            "https://api-singapore.klingai.com/v1/videos/text2video",
            headers=get_kling_headers(),
            json=payload,
            timeout=90
        )

        try:
            data = r.json()
        except:
            data = {"raw_text": r.text}

        print("KLING SUBMIT STATUS:", r.status_code)
        print("KLING SUBMIT RESPONSE:", data)

        if r.status_code != 200:
            return {
                "ok": False,
                "reason": f"HTTP_{r.status_code}",
                "data": data
            }

        task_id = (
            data.get("data", {}).get("task_id")
            or data.get("data", {}).get("id")
            or data.get("task_id")
            or data.get("id")
        )

        if not task_id:
            return {
                "ok": False,
                "reason": "NO_TASK_ID",
                "data": data
            }

        return {
            "ok": True,
            "provider": "kling",
            "mode": mode,
            "task_id": task_id,
            "data": data
        }

    except Exception as e:
        return {
            "ok": False,
            "reason": f"SUBMIT_EXCEPTION_{repr(e)}"
        }


def poll_kling_text_task(task_id, max_wait=600, interval=10):
    started = time.time()

    while time.time() - started < max_wait:
        try:
            r = requests.get(
                f"https://api-singapore.klingai.com/v1/videos/text2video/{task_id}",
                headers=get_kling_headers(),
                timeout=60
            )

            try:
                data = r.json()
            except:
                data = {"raw_text": r.text}

            print("KLING POLL STATUS:", r.status_code)
            print("KLING POLL RESPONSE:", data)

            if r.status_code != 200:
                time.sleep(interval)
                continue

            data_block = data.get("data", {})
            task_status = str(data_block.get("task_status", "")).lower()

            if task_status in ["submitted", "processing", "running", "pending", "created"]:
                time.sleep(interval)
                continue

            if task_status in ["succeed", "success", "completed", "done", "finished"]:
                task_result = data_block.get("task_result", {})
                videos = task_result.get("videos", [])

                if videos and isinstance(videos, list):
                    first_video = videos[0] or {}
                    video_url = first_video.get("url", "")
                    if video_url:
                        return {
                            "ok": True,
                            "url": video_url,
                            "raw": data
                        }

                return {
                    "ok": False,
                    "reason": "NO_VIDEO_URL",
                    "raw": data
                }

            if task_status in ["failed", "fail", "error", "canceled", "cancelled"]:
                return {
                    "ok": False,
                    "reason": f"TASK_{task_status.upper()}",
                    "raw": data
                }

            time.sleep(interval)

        except Exception as e:
            print("KLING POLL ERROR:", repr(e))
            time.sleep(interval)

    return {
        "ok": False,
        "reason": "TIMEOUT_WAITING_VIDEO"
    }


'''

if old not in text:
    print("SUBMIT_FUNC_NOT_FOUND")
    raise SystemExit

text = text.replace(old, new, 1)

old2 = '''            try:
                kling_result = submit_kling_task(task)

                if kling_result.get("ok"):
                    bot.send_message(
                        user_id,
                        f"🎥 Видео готово\\nРежим: {mode}\\nРазмер: {size}\\nДлительность: {duration} сек"
                    )
                else:
                    bot.send_message(
                        user_id,
                        f"🎥 Видео-задача взята в обработку\\nРежим: {mode}\\nРазмер: {size}\\nДлительность: {duration} сек\\n\\nПока работает тестовый этап подключения Kling."
                    )

                print(f"VIDEO WORKER: done user={user_id} mode={mode}")
            finally:
                if user_id is not None:
                    clear_video_processing_task(user_id)'''

new2 = '''            try:
                kling_result = submit_kling_task(task)

                if kling_result.get("ok"):
                    task_id = kling_result.get("task_id", "")
                    bot.send_message(
                        user_id,
                        f"🎥 Видео-задача отправлена в Kling\\nРежим: {mode}\\nРазмер: {size}\\nДлительность: {duration} сек\\nTask ID: {task_id}"
                    )

                    if mode == "text":
                        final_result = poll_kling_text_task(task_id)

                        if final_result.get("ok"):
                            video_url = final_result.get("url", "")

                            try:
                                bot.send_video(
                                    user_id,
                                    video_url,
                                    caption=f"🎥 Видео готово\\nРежим: {mode}\\nРазмер: {size}\\nДлительность: {duration} сек"
                                )
                            except Exception as send_video_error:
                                print("KLING SEND VIDEO ERROR:", repr(send_video_error))
                                bot.send_message(
                                    user_id,
                                    f"🎥 Видео готово\\n{video_url}"
                                )
                        else:
                            bot.send_message(
                                user_id,
                                f"❌ Kling не отдал готовое видео: {final_result.get('reason', 'UNKNOWN_ERROR')}"
                            )
                    else:
                        bot.send_message(
                            user_id,
                            f"🎥 Режим {mode} пока ещё не подключён к реальному Kling."
                        )
                else:
                    bot.send_message(
                        user_id,
                        f"❌ Ошибка отправки задачи в Kling: {kling_result.get('reason', 'UNKNOWN_ERROR')}"
                    )

                print(f"VIDEO WORKER: done user={user_id} mode={mode}")
            finally:
                if user_id is not None:
                    clear_video_processing_task(user_id)'''

if old2 not in text:
    print("VIDEO_WORKER_BLOCK_NOT_FOUND")
    raise SystemExit

text = text.replace(old2, new2, 1)

p.write_text(text, encoding='utf-8')
print("PATCH_OK")
PY
