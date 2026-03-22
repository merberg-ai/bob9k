import sys
sys.path.insert(0, 'e:/SRC/bob9k')
try:
    from bob9k.app import create_app
    app = create_app()
    print("ROUTES:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.methods} {rule.rule}")
    print("\nSUCCESS")
except Exception as e:
    print(f"FAILED TO LOAD: {e}")
    import traceback
    traceback.print_exc()
