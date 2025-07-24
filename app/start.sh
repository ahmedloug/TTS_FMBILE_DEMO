# # Définir le sink par défaut
# pactl set-default-sink bluez_sink.F8_5C_7E_1B_1F_4C.a2dp_sink

# Start uvicorn in foreground
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &

# Start listener.py in background
python listener.py 