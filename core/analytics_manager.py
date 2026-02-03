"""
Analytics management for Claude Code Manager.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .config import Config
from .models import DailyActivity, ModelUsage


# Pricing per 1M tokens (as of 2025)
MODEL_PRICING = {
    'claude-opus-4-5-20251101': {'input': 15.0, 'output': 75.0, 'cache_read': 1.5, 'cache_create': 18.75},
    'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0, 'cache_read': 0.3, 'cache_create': 3.75},
    'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0, 'cache_read': 0.3, 'cache_create': 3.75},
    'claude-3-5-haiku-20241022': {'input': 0.8, 'output': 4.0, 'cache_read': 0.08, 'cache_create': 1.0},
    'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0, 'cache_read': 1.5, 'cache_create': 18.75},
    'claude-3-sonnet-20240229': {'input': 3.0, 'output': 15.0, 'cache_read': 0.3, 'cache_create': 3.75},
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25, 'cache_read': 0.025, 'cache_create': 0.3},
}


class AnalyticsManager:
    """Manages usage analytics and cost tracking."""

    def __init__(self, config: Config):
        self.config = config
        self._stats_cache: Optional[Dict[str, Any]] = None

    def get_stats_cache(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load stats cache."""
        if self._stats_cache is not None and not force_refresh:
            return self._stats_cache

        self._stats_cache = self.config.get_stats_cache()
        return self._stats_cache

    def get_daily_activity(self, days: int = 30) -> List[DailyActivity]:
        """Get daily activity for the specified number of days."""
        stats = self.get_stats_cache()
        daily_data = stats.get('dailyActivity', [])

        activities = []
        for item in daily_data:
            activities.append(DailyActivity(
                date=item.get('date', ''),
                message_count=item.get('messageCount', 0),
                session_count=item.get('sessionCount', 0),
                tool_call_count=item.get('toolCallCount', 0)
            ))

        # Sort by date
        activities.sort(key=lambda x: x.date)

        # Filter to last N days
        if days > 0:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            activities = [a for a in activities if a.date >= cutoff]

        return activities

    def get_model_usage(self) -> Dict[str, ModelUsage]:
        """Get usage statistics by model."""
        stats = self.get_stats_cache()
        model_data = stats.get('modelUsage', {})

        usage = {}
        for model, data in model_data.items():
            usage[model] = ModelUsage(
                model=model,
                input_tokens=data.get('inputTokens', 0),
                output_tokens=data.get('outputTokens', 0),
                cache_read_tokens=data.get('cacheReadInputTokens', 0),
                cache_creation_tokens=data.get('cacheCreationInputTokens', 0),
                web_search_requests=data.get('webSearchRequests', 0),
                cost_usd=data.get('costUSD', 0.0)
            )

        return usage

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int,
                       cache_read: int = 0, cache_create: int = 0) -> float:
        """Calculate cost for token usage."""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING.get('claude-sonnet-4-20250514'))

        cost = 0.0
        cost += (input_tokens / 1_000_000) * pricing['input']
        cost += (output_tokens / 1_000_000) * pricing['output']
        cost += (cache_read / 1_000_000) * pricing['cache_read']
        cost += (cache_create / 1_000_000) * pricing['cache_create']

        return cost

    def get_total_cost(self) -> float:
        """Calculate total estimated cost."""
        usage = self.get_model_usage()
        total = 0.0

        for model, data in usage.items():
            total += self.calculate_cost(
                model,
                data.input_tokens,
                data.output_tokens,
                data.cache_read_tokens,
                data.cache_creation_tokens
            )

        return total

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        stats = self.get_stats_cache()
        usage = self.get_model_usage()

        total_input = sum(u.input_tokens for u in usage.values())
        total_output = sum(u.output_tokens for u in usage.values())
        total_cache_read = sum(u.cache_read_tokens for u in usage.values())
        total_cache_create = sum(u.cache_creation_tokens for u in usage.values())

        return {
            'total_sessions': stats.get('totalSessions', 0),
            'total_messages': stats.get('totalMessages', 0),
            'first_session_date': stats.get('firstSessionDate'),
            'total_input_tokens': total_input,
            'total_output_tokens': total_output,
            'total_cache_read_tokens': total_cache_read,
            'total_cache_create_tokens': total_cache_create,
            'total_cost': self.get_total_cost(),
            'longest_session': stats.get('longestSession', {}),
            'hour_distribution': stats.get('hourCounts', {})
        }

    def get_tokens_by_day(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get token usage by day."""
        stats = self.get_stats_cache()
        daily_tokens = stats.get('dailyModelTokens', [])

        result = []
        for item in daily_tokens:
            date = item.get('date', '')
            tokens_by_model = item.get('tokensByModel', {})

            total = sum(tokens_by_model.values())
            result.append({
                'date': date,
                'total_tokens': total,
                'by_model': tokens_by_model
            })

        # Sort by date
        result.sort(key=lambda x: x['date'])

        # Filter to last N days
        if days > 0:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            result = [r for r in result if r['date'] >= cutoff]

        return result

    def get_cost_by_period(self, period: str = 'day') -> List[Dict[str, Any]]:
        """Get cost breakdown by period (day, week, month)."""
        tokens_by_day = self.get_tokens_by_day(days=365)

        if period == 'day':
            return [
                {
                    'period': t['date'],
                    'cost': self._estimate_cost_for_tokens(t['by_model'])
                }
                for t in tokens_by_day
            ]

        elif period == 'week':
            weekly = defaultdict(lambda: defaultdict(int))
            for t in tokens_by_day:
                date = datetime.strptime(t['date'], '%Y-%m-%d')
                week_start = (date - timedelta(days=date.weekday())).strftime('%Y-%m-%d')
                for model, tokens in t['by_model'].items():
                    weekly[week_start][model] += tokens

            return [
                {'period': week, 'cost': self._estimate_cost_for_tokens(dict(models))}
                for week, models in sorted(weekly.items())
            ]

        elif period == 'month':
            monthly = defaultdict(lambda: defaultdict(int))
            for t in tokens_by_day:
                month = t['date'][:7]  # YYYY-MM
                for model, tokens in t['by_model'].items():
                    monthly[month][model] += tokens

            return [
                {'period': month, 'cost': self._estimate_cost_for_tokens(dict(models))}
                for month, models in sorted(monthly.items())
            ]

        return []

    def _estimate_cost_for_tokens(self, tokens_by_model: Dict[str, int]) -> float:
        """Estimate cost from token counts (assuming 1:3 input:output ratio)."""
        total = 0.0
        for model, tokens in tokens_by_model.items():
            # Assume 75% input, 25% output ratio
            input_tokens = int(tokens * 0.75)
            output_tokens = int(tokens * 0.25)
            total += self.calculate_cost(model, input_tokens, output_tokens)
        return total

    def export_analytics(self, filepath: Path, format: str = 'json') -> bool:
        """Export analytics data to file."""
        try:
            data = {
                'summary': self.get_summary_stats(),
                'daily_activity': [
                    {
                        'date': a.date,
                        'message_count': a.message_count,
                        'session_count': a.session_count,
                        'tool_call_count': a.tool_call_count
                    }
                    for a in self.get_daily_activity(days=365)
                ],
                'model_usage': {
                    model: {
                        'input_tokens': u.input_tokens,
                        'output_tokens': u.output_tokens,
                        'cache_read_tokens': u.cache_read_tokens,
                        'cache_creation_tokens': u.cache_creation_tokens,
                        'estimated_cost': self.calculate_cost(
                            model, u.input_tokens, u.output_tokens,
                            u.cache_read_tokens, u.cache_creation_tokens
                        )
                    }
                    for model, u in self.get_model_usage().items()
                },
                'tokens_by_day': self.get_tokens_by_day(days=365),
                'export_date': datetime.now().isoformat()
            }

            if format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            elif format == 'csv':
                import csv
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Date', 'Messages', 'Sessions', 'Tool Calls', 'Tokens'])
                    for activity in data['daily_activity']:
                        tokens = next(
                            (t['total_tokens'] for t in data['tokens_by_day'] if t['date'] == activity['date']),
                            0
                        )
                        writer.writerow([
                            activity['date'],
                            activity['message_count'],
                            activity['session_count'],
                            activity['tool_call_count'],
                            tokens
                        ])

            return True
        except IOError:
            return False
