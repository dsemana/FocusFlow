from app.startup import create_server_app

app = create_server_app()
if __name__ == "__main__":
    import os
    from waitress import create_server

    port = int(os.getenv("PORT", "5000"))
    server = create_server(app, host="127.0.0.1", port=port)
    print(f"FocusFlow is ready at http://127.0.0.1:{port}", flush=True)
    print("Open the URL and choose Create an account to register.", flush=True)
    server.run()
