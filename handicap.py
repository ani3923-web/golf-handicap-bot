import json
import os
from datetime import datetime


class HandicapManager:
    def __init__(self, data_file: str):
        self.data_file = data_file
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def _calc_hdcp(self, scores: list) -> float:
        recent = scores[-20:]
        diffs  = [s['score'] - s['cr'] for s in recent]
        best8  = sorted(diffs)[:8]
        hdcp   = (sum(best8) / len(best8)) * 0.96
        return round(hdcp, 1)

    def add_score(self, user_id: str, user_name: str,
                  score: int, cr: float, course: str) -> dict:
        if user_id not in self.data:
            self.data[user_id] = {'name': user_name, 'scores': []}
        self.data[user_id]['name'] = user_name
        entry = {
            'score':  score,
            'cr':     cr,
            'course': course,
            'date':   datetime.now().strftime('%Y-%m-%d')
        }
        self.data[user_id]['scores'].append(entry)
        self._save()
        scores_list = self.data[user_id]['scores']
        hdcp        = self._calc_hdcp(scores_list)
        diff        = score - cr
        rounds      = len(scores_list)
        diff_str = f'+{diff:.1f}' if diff >= 0 else f'{diff:.1f}'
        personal_message = (
            f"【スコア登録完了】\n"
            f"名前　：{user_name}\n"
            f"コース：{course}（CR {cr}）\n"
            f"スコア：{score}（差分 {diff_str}）\n"
            f"HDCP　：{hdcp}（{rounds}R目）"
        )
        return {'hdcp': hdcp, 'personal_message': personal_message}

    def get_ranking_message(self) -> str:
        if not self.data:
            return "まだスコアが登録されていません。"
        ranking = []
        for user_id, info in self.data.items():
            if info['scores']:
                hdcp   = self._calc_hdcp(info['scores'])
                rounds = len(info['scores'])
                ranking.append((info['name'], hdcp, rounds))
        ranking.sort(key=lambda x: x[1])
        today = datetime.now().strftime('%Y年%m月%d日')
        lines = [f"【ハンディキャップランキング】\n{today}現在\n"]
        medals = ['🥇', '🥈', '🥉']
        for i, (name, hdcp, rounds) in enumerate(ranking):
            medal = medals[i] if i < 3 else f'{i+1}位'
            lines.append(f"{medal} {name}　HDCP {hdcp}　({rounds}R)")
        lines.append(f"\n参加人数：{len(ranking)}名")
        return '\n'.join(lines)
