"""Run a seeded local testing instance without touching the normal database."""

import argparse

from app.demo import create_demo_app, DEMO_EMAIL, DEMO_PASSWORD


def main():
    from waitress import create_server

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()
    app = create_demo_app()
    server = create_server(app, host="127.0.0.1", port=args.port)
    print(f"FocusFlow testing instance: http://127.0.0.1:{args.port}", flush=True)
    print(f"Demo email: {DEMO_EMAIL}\nDemo password: {DEMO_PASSWORD}", flush=True)
    print(
        "Sample data is separate from your normal workspace. Testing changes persist on restart.",
        flush=True,
    )
    server.run()


if __name__ == "__main__":
    main()
