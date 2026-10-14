"""
Simple runner for SkillPulse backend.

Usage:
  python run_all.py train         # runs training script to generate model artifacts
  python run_all.py serve         # starts the Flask API (will block)
  python run_all.py test          # sends a sample POST to /api/recommend-courses
  python run_all.py all           # train, start server, test, then stop server

The script expects to be executed from the `backend/` directory or will set cwd accordingly.
"""
import argparse
import subprocess
import sys
import time
import os
import requests


def run_train(cwd):
    print('Running training script...')
    res = subprocess.run([sys.executable, 'train_and_save_models.py'], cwd=cwd)
    if res.returncode != 0:
        raise SystemExit('Training failed')
    print('Training completed.')


def start_server(cwd):
    print('Starting Flask server...')
    proc = subprocess.Popen([sys.executable, 'app.py'], cwd=cwd)
    return proc


def wait_for_health(url, timeout=15):
    print(f'Waiting for server health at {url}...')
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print('Server healthy.')
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def run_test(url, payload=None):
    payload = payload or {'target_skill': 'Python', 'top_k': 3}
    print('Sending test recommendation request...')
    r = requests.post(url, json=payload, timeout=10)
    print('Status:', r.status_code)
    try:
        print('Response:', r.json())
    except Exception:
        print('Non-JSON response:', r.text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', choices=['train', 'serve', 'test', 'all'])
    args = parser.parse_args()

    cwd = os.path.dirname(__file__)
    health_url = 'http://127.0.0.1:5000/api/health'
    rec_url = 'http://127.0.0.1:5000/api/recommend-courses'

    if args.cmd == 'train':
        run_train(cwd)

    elif args.cmd == 'serve':
        # start server in foreground
        subprocess.run([sys.executable, 'app.py'], cwd=cwd)

    elif args.cmd == 'test':
        run_test(rec_url)

    elif args.cmd == 'all':
        run_train(cwd)
        proc = start_server(cwd)
        try:
            ok = wait_for_health(health_url, timeout=20)
            if not ok:
                raise SystemExit('Server did not become healthy in time')
            run_test(rec_url)
        finally:
            print('Stopping server...')
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == '__main__':
    main()
