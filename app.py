from flask import Flask, request, jsonify, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    MemberJoinedEvent
)
import os
import json
from handicap import HandicapManager

app = Flask(__name__, static_folder='static')

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN', '')
LINE_CHANNEL_SECRET       = os.environ.get('LINE_CHANNEL_SECRET', '')
LIFF_ID                   = os.environ.get('LIFF_ID', '')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler      = WebhookHandler(LINE_CHANNEL_SECRET)
hc_manager   = HandicapManager('data/scores.json')
group_id_cache = {}
DEFAULT_GROUP_ID = os.environ.get('GROUP_ID', '')
@app.route('/liff')
def liff_page():
    return send_from_directory('static', 'liff.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    return 'OK', 200

@app.route('/submit_score', methods=['POST'])
def submit_score():
    data       = request.json
    user_id    = data.get('userId')
    user_name  = data.get('userName')
    user_id_tmp = data.get('userId')
    group_id  = data.get('groupId') or group_id_cache.get(user_id_tmp, '') or DEFAULT_GROUP_ID
 
    score      = int(data.get('score'))
    cr         = float(data.get('cr'))
    course     = data.get('course')
    result = hc_manager.add_score(user_id, user_name, score, cr, course)
    messages = [
        TextSendMessage(text=result['personal_message']),
        TextSendMessage(text=hc_manager.get_ranking_message())
    ]
    line_bot_api.push_message(group_id, messages)
    return jsonify({'status': 'ok'})

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
        text     = event.message.text.strip()
        group_id = event.source.group_id if hasattr(event.source, 'group_id') else None
        print(f"DEBUG group_id: {group_id}")
        if group_id:
            group_id_cache[event.source.user_id] = group_id
        if text == 'ランキング' and group_id:
            msg = hc_manager.get_ranking_message()
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
@handler.add(MemberJoinedEvent)
def handle_member_join(event):
    group_id = event.source.group_id
    for member in event.joined.members:
        profile  = line_bot_api.get_group_member_profile(group_id, member.user_id)
        welcome  = (
            f"🏌️ {profile.display_name}さん、ゴルフ部へようこそ！\n\n"
            f"スコアを入力するにはメニューの「スコア入力」ボタンをタップしてください。\n"
            f"初回入力時に自動登録されます。"
        )
        line_bot_api.push_message(group_id, TextSendMessage(text=welcome))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
