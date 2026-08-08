"""
NOVA Core Application Root Entry Point with Token Streaming
"""
import sys
import argparse
from nova.bootstrap import ApplicationBootstrap


def run_interactive_chat(app: ApplicationBootstrap) -> None:
    """Runs interactive command line chat interface with NOVA with real-time streaming."""
    ai_engine = app.ai_engine
    if not ai_engine:
        print("\n\033[91m[Error]: AI Engine not available.\033[0m")
        return

    print("\n\033[96m============================================================\033[0m")
    print("  \033[1mNOVA Interactive Conversation Session (Streaming Active)\033[0m")
    print("  Type \033[93m/help\033[0m for available session commands or \033[93m/exit\033[0m to quit.")
    print("\033[96m============================================================\033[0m\n")

    while True:
        try:
            active_name = ai_engine.session_manager.active_session_name
            user_input = input(f"\033[94mNOVA [{active_name}] > \033[0m").strip()

            if not user_input:
                continue

            # Command Handling
            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                print("\033[90mExiting NOVA session. Goodbye!\033[0m")
                break

            elif user_input.lower() == "/help":
                print("\n\033[1mSession Commands:\033[0m")
                print("  \033[93m/session\033[0m             - List all sessions")
                print("  \033[93m/session create <name>\033[0m - Create and switch to a new session")
                print("  \033[93m/session switch <id>\033[0m   - Switch active session")
                print("  \033[93m/status\033[0m              - Display AI status metrics")
                print("  \033[93m/clear\033[0m               - Clear active session history")
                print("  \033[93m/exit\033[0m                - Quit interactive mode\n")
                continue

            elif user_input.lower() == "/session":
                sessions = ai_engine.list_sessions()
                print("\n\033[1mAvailable Sessions:\033[0m")
                for s in sessions:
                    badge = "\033[92m[ACTIVE]\033[0m" if s["is_active"] else "        "
                    print(f"  {badge} {s['name']:<20} (ID: {s['session_id']}, Messages: {s['message_count']})")
                print()
                continue

            elif user_input.lower().startswith("/session create "):
                sess_name = user_input[16:].strip()
                if sess_name:
                    sid = ai_engine.create_session(sess_name)
                    print(f"\033[92mCreated and switched to session '{sess_name}' ({sid})\033[0m\n")
                continue

            elif user_input.lower().startswith("/session switch "):
                sid = user_input[16:].strip()
                if sid:
                    if ai_engine.switch_session(sid):
                        print(f"\033[92mSwitched to session ID '{sid}'\033[0m\n")
                    else:
                        print(f"\033[91mSession ID '{sid}' not found.\033[0m\n")
                continue

            elif user_input.lower() == "/status":
                st = ai_engine.get_ai_status()
                print("\n\033[1mAI Engine Telemetry:\033[0m")
                for k, v in st.items():
                    print(f"  • {k:<20}: {v}")
                print()
                continue

            elif user_input.lower() == "/clear":
                ai_engine.session_manager.clear_session(ai_engine.session_manager.active_session_id)
                print("\033[92mActive session conversation cleared.\033[0m\n")
                continue

            # Process AI Chat Prompt with Real-Time Streaming
            print("\033[96mNOVA:\033[0m ", end="", flush=True)
            for chunk in ai_engine.chat_stream(user_input):
                print(chunk, end="", flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\033[90mSession interrupted. Exiting.\033[0m")
            break
        except Exception as e:
            print(f"\n\033[91m[Error]: {e}\033[0m\n")


def main() -> None:
    """
    Main entry point for starting NOVA.
    """
    parser = argparse.ArgumentParser(description="NOVA AI Assistant Platform")
    parser.add_argument("--chat", action="store_true", help="Launch interactive CLI chat session")
    parser.add_argument("--prompt", type=str, help="Execute single completion prompt and exit")
    parser.add_argument("--session", type=str, help="Session name or ID to use")
    args = parser.parse_args()

    app = ApplicationBootstrap()
    success = app.initialize()
    if not success:
        sys.exit(1)

    try:
        if args.prompt:
            print(f"\n\033[94mUser Prompt:\033[0m {args.prompt}")
            print(f"\033[96mNOVA Response:\033[0m ", end="", flush=True)
            for chunk in app.ai_engine.chat_stream(args.prompt, session_id=args.session):
                print(chunk, end="", flush=True)
            print("\n")
        elif args.chat:
            run_interactive_chat(app)
        else:
            print("\033[90mBootstrap completed. Use `--chat` to launch interactive session or `--prompt \"...\"` to query NOVA.\033[0m")
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
