from flask import Flask, render_template, request, jsonify
from mqtt_manager import MqttManager
from scheduler import SmartScheduler
from database import init_db, get_groups, save_group, delete_group, get_scenarios, save_scenario, delete_scenario
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
init_db()

mqtt = MqttManager()
scheduler = SmartScheduler(mqtt)

mqtt.start()
scheduler.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/devices')
def api_devices():
    return jsonify(mqtt.get_all_devices())

@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.get_json()
    friendly = data.get('friendly_name')
    command = data.get('command')
    if not friendly or not command:
        return jsonify({"error": "friendly_name и command обязательны"}), 400
    mqtt.send_command(friendly, command)
    return jsonify({"success": True})

@app.route('/api/groups', methods=['GET', 'POST', 'DELETE'])
def api_groups():
    if request.method == 'GET':
        return jsonify(get_groups())
    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        devices = data.get('devices', [])
        save_group(name, devices)
        return jsonify({"success": True})
    elif request.method == 'DELETE':
        data = request.get_json()
        name = data.get('name')
        delete_group(name)
        return jsonify({"success": True})

@app.route('/api/groups/command', methods=['POST'])
def api_group_command():
    data = request.get_json()
    group_name = data.get('group_name')
    command = data.get('command')
    groups = get_groups()
    if group_name not in groups:
        return jsonify({"error": "Группа не найдена"}), 404
    mqtt.send_group_command(groups[group_name], command)
    return jsonify({"success": True})

@app.route('/api/scenarios', methods=['GET', 'POST'])
def api_scenarios():
    if request.method == 'GET':
        return jsonify(get_scenarios())
    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        trigger_type = data.get('trigger_type')
        config = data.get('config')
        save_scenario(name, trigger_type, config)
        scheduler.reload_jobs()
        return jsonify({"success": True})

@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
def api_delete_scenario(scenario_id):
    delete_scenario(scenario_id)
    scheduler.reload_jobs()
    return jsonify({"success": True})

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        mqtt.stop()
        scheduler.stop()