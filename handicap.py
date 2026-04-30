import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor


class HandicapManager:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
        self.conn.autocommit = True

    def _get_cursor(self):
        return self.conn.cursor(cursor_factory=RealDictCursor)

    def _calc_hdcp(self, scores: list) -> float:
        recent = scores[-20:]
        diffs  = [s['score'] - s['cr'] for s in recent]
        best8  = sorted(diffs)[:8]
        hdcp   = (sum(best8) / len(best8)) * 0.96
        return round(hdcp, 1)

    def add_score(self, group_id: str, user_id: str, user_name: str,
                  score: int, cr: float, course: str) -> dict:
        date = datetime.now().strftime('%Y-%m-%d')
        with self._get_cursor() as cur:
            cur.execute(
                """INSERT INTO scores (group_id, user_id, display_name, score, cr, course, date)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (group_id, user_id, user_name, score, cr, course, date)
            )
            cur.execute(
                "SELECT score, cr FROM scores WHERE group_id=%s AND user_id=%s ORDER BY created_at",
                (group_id, user_id)
            )
            rows = cur.fetchall()
        hdcp   = self._calc_hdcp(rows)
        diff   = score - cr
        rounds = len(rows)
        diff_str = f'+{diff:.1f}' if diff >= 0 else f'{diff:.1f}'
        personal_message = (
            f"【スコア登録完了】\n"
            f"名前　：{user_name}\n"
            f"コース：{course}（CR {cr}）\n"
            f"スコア：{score}（差分 {diff_str}）\n"
            f"HDCP　：{hdcp}（{rounds}R目）"
        )
        return {'hdcp': hdcp, 'personal_message': personal_message}

    def get_ranking_message(self, group_id: str) -> str:
        with self._get_cursor() as cur:
            cur.execute(
                "SELECT user_id, display_name, score, cr FROM scores WHERE group_id=%s ORDER BY created_at",
                (group_id,)
            )
            rows = cur.fetchall()
        if not rows:
            return "まだスコアが登録されていません。"
        users = {}
        for row in rows:
            uid = row['user_id']
            if uid not in users:
                users[uid] = {'name': row['display_name'], 'scores': []}
            users[uid]['scores'].append({'score': row['score'], 'cr': row['cr']})
        ranking = []
        for uid, info in users.items():
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

    def get_all_scores(self, group_id: str) -> list:
        with self._get_cursor() as cur:
            cur.execute(
                "SELECT id, display_name, score, cr, course, date FROM scores WHERE group_id=%s ORDER BY created_at DESC",
                (group_id,)
            )
            return cur.fetchall()

    def delete_score(self, score_id: int, group_id: str) -> bool:
        with self._get_cursor() as cur:
            cur.execute(
                "DELETE FROM scores WHERE id=%s AND group_id=%s",
                (score_id, group_id)
            )
            return cur.rowcount > 0
