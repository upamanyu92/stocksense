"""
AI portfolio analysis service - generates portfolio summaries,
risk assessments, and recommendations using available LLMs with fallback.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.db.session_manager import get_session_manager
from app.services.portfolio_service import PortfolioService

logger = logging.getLogger(__name__)

# Fallback templates when no LLM is available
FALLBACK_TEMPLATES = {
    'summary': (
        "📊 **Portfolio Summary**\n\n"
        "You have **{holdings_count}** holdings with a total investment of **₹{total_invested:,.2f}**.\n"
        "Current portfolio value: **₹{total_current:,.2f}**\n"
        "Overall P&L: **₹{total_pnl:,.2f}** ({pnl_percent:+.2f}%)\n\n"
        "{top_holdings}\n\n"
        "_Note: This is a template-based summary. Connect an AI model for deeper analysis._"
    ),
    'risk': (
        "⚠️ **Risk Assessment**\n\n"
        "Portfolio concentration: {concentration_status}\n"
        "Number of holdings: {holdings_count}\n"
        "Top holding allocation: {top_allocation:.1f}%\n\n"
        "**Diversification:** {diversification_note}\n\n"
        "_Note: Connect an AI model for a comprehensive risk analysis._"
    ),
    'allocation': (
        "📈 **Asset Allocation**\n\n"
        "{allocation_breakdown}\n\n"
        "_Note: Connect an AI model for allocation recommendations._"
    ),
}


class PortfolioAnalysisService:
    """AI-powered portfolio analysis with LLM fallback."""

    @staticmethod
    def analyze_portfolio(
        user_id: int,
        analysis_type: str = 'summary',
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate portfolio analysis using best available LLM.
        Falls back to template-based analysis if no LLM is available.
        """
        db = get_session_manager()

        # Check cache (1-hour expiry)
        if not force_refresh:
            cached = db.fetch_one(
                '''SELECT content, model_used, confidence, created_at
                   FROM portfolio_analysis
                   WHERE user_id = ? AND analysis_type = ?
                     AND expires_at > datetime('now')
                   ORDER BY created_at DESC LIMIT 1''',
                (user_id, analysis_type),
            )
            if cached:
                return {
                    'success': True,
                    'analysis': cached['content'],
                    'model_used': cached['model_used'],
                    'confidence': cached['confidence'],
                    'cached': True,
                    'generated_at': cached['created_at'],
                }

        # Get portfolio data
        holdings = PortfolioService.get_holdings(user_id)
        summary = PortfolioService.get_portfolio_summary(user_id)
        allocation = PortfolioService.get_asset_allocation(user_id)

        if not holdings:
            return {
                'success': True,
                'analysis': 'No portfolio holdings found. Add holdings or import a brokerage statement to get AI analysis.',
                'model_used': 'none',
                'confidence': 0,
                'cached': False,
            }

        # Try LLMs in priority order
        model_used = 'fallback'
        analysis_text = ''
        confidence = 0.0

        # Try Ollama first
        try:
            result = PortfolioAnalysisService._analyze_with_ollama(
                holdings, summary, allocation, analysis_type,
            )
            if result:
                analysis_text = result
                model_used = 'ollama'
                confidence = 0.85
        except Exception as e:
            logger.debug(f"Ollama analysis unavailable: {e}")

        # Try Gemini if Ollama failed
        if not analysis_text:
            try:
                result = PortfolioAnalysisService._analyze_with_gemini(
                    holdings, summary, allocation, analysis_type,
                )
                if result:
                    analysis_text = result
                    model_used = 'gemini'
                    confidence = 0.9
            except Exception as e:
                logger.debug(f"Gemini analysis unavailable: {e}")

        # Fallback to template
        if not analysis_text:
            analysis_text = PortfolioAnalysisService._generate_fallback(
                holdings, summary, allocation, analysis_type,
            )
            model_used = 'fallback'
            confidence = 0.5

        # Cache the result
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        db.insert(
            '''INSERT INTO portfolio_analysis
               (user_id, analysis_type, content, model_used, confidence, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, analysis_type, analysis_text, model_used, confidence, expires_at),
        )

        return {
            'success': True,
            'analysis': analysis_text,
            'model_used': model_used,
            'confidence': confidence,
            'cached': False,
            'generated_at': datetime.now().isoformat(),
        }

    @staticmethod
    def get_model_status() -> Dict[str, Any]:
        """Check availability of all AI models."""
        status = {
            'ollama': {'available': False, 'model': None},
            'gemini': {'available': False, 'model': None},
            'copilot': {'available': False, 'model': None},
            'active_model': 'none',
        }

        # Check Ollama
        try:
            import ollama
            models = ollama.list()
            if models and hasattr(models, 'models') and models.models:
                status['ollama']['available'] = True
                status['ollama']['model'] = models.models[0].model if models.models else None
                status['active_model'] = 'ollama'
        except Exception:
            pass

        # Check Gemini
        try:
            from app.db.services.system_settings_service import SystemSettingsService
            gemini_key = SystemSettingsService.get_setting('gemini_api_key')
            if gemini_key:
                status['gemini']['available'] = True
                status['gemini']['model'] = 'gemini-pro'
                if status['active_model'] == 'none':
                    status['active_model'] = 'gemini'
        except Exception:
            pass

        # Check system setting for active LLM
        try:
            from app.db.services.system_settings_service import SystemSettingsService
            active = SystemSettingsService.get_setting('active_llm_agent', 'ollama')
            if active and status.get(active, {}).get('available'):
                status['active_model'] = active
        except Exception:
            pass

        return status

    # ------------------------------------------------------------------ #
    #  LLM backends
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_prompt(holdings, summary, allocation, analysis_type):
        """Build a prompt for LLM analysis."""
        holdings_text = '\n'.join(
            f"- {h['stock_symbol']}: {h['quantity']} shares @ avg ₹{h['avg_buy_price']:.2f}, "
            f"P&L: ₹{h.get('pnl', 0):.2f} ({h.get('pnl_percent', 0):.1f}%)"
            for h in holdings[:20]  # Limit to 20 for prompt size
        )

        alloc_text = '\n'.join(
            f"- {a['stock_symbol']}: {a['allocation_percent']:.1f}%"
            for a in allocation[:15]
        )

        base_context = (
            f"Portfolio has {summary['holdings_count']} holdings.\n"
            f"Total invested: ₹{summary['total_invested']:,.2f}\n"
            f"Current value: ₹{summary['total_current_value']:,.2f}\n"
            f"P&L: ₹{summary['total_pnl']:,.2f} ({summary['pnl_percent']:+.2f}%)\n\n"
            f"Holdings:\n{holdings_text}\n\n"
            f"Allocation:\n{alloc_text}"
        )

        prompts = {
            'summary': (
                "You are a financial advisor. Analyze this Indian stock portfolio and provide "
                "a concise summary with key observations about performance, concentration, "
                "and any notable patterns. Use markdown formatting.\n\n" + base_context
            ),
            'risk': (
                "You are a risk analyst. Assess the risk profile of this portfolio. Consider "
                "concentration risk, sector exposure, volatility, and diversification. "
                "Rate the overall risk level and provide specific suggestions. Use markdown.\n\n"
                + base_context
            ),
            'allocation': (
                "You are an investment advisor. Analyze the asset allocation of this portfolio. "
                "Comment on diversification, suggest rebalancing if needed, and identify "
                "over/under-weighted positions. Use markdown.\n\n" + base_context
            ),
            'recommendation': (
                "You are a wealth advisor. Based on this portfolio, provide actionable "
                "recommendations for improvement. Consider risk management, diversification, "
                "and potential opportunities. Be specific but concise. Use markdown.\n\n"
                + base_context
            ),
        }

        return prompts.get(analysis_type, prompts['summary'])

    @staticmethod
    def _analyze_with_ollama(holdings, summary, allocation, analysis_type) -> Optional[str]:
        """Generate analysis using local Ollama model."""
        import ollama

        prompt = PortfolioAnalysisService._build_prompt(
            holdings, summary, allocation, analysis_type,
        )

        response = ollama.chat(
            model='phi4-mini',
            messages=[{'role': 'user', 'content': prompt}],
        )

        if response and hasattr(response, 'message'):
            return response.message.content
        return None

    @staticmethod
    def _analyze_with_gemini(holdings, summary, allocation, analysis_type) -> Optional[str]:
        """Generate analysis using Google Gemini."""
        from google import genai

        prompt = PortfolioAnalysisService._build_prompt(
            holdings, summary, allocation, analysis_type,
        )

        try:
            from app.db.services.system_settings_service import SystemSettingsService
            api_key = SystemSettingsService.get_setting('gemini_api_key')
            if not api_key:
                return None

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            logger.debug(f"Gemini analysis failed: {e}")

        return None

    # ------------------------------------------------------------------ #
    #  Fallback templates
    # ------------------------------------------------------------------ #

    @staticmethod
    def _generate_fallback(holdings, summary, allocation, analysis_type) -> str:
        """Generate template-based analysis when no LLM is available."""
        if analysis_type == 'summary':
            top_holdings_text = ''
            if allocation:
                top_holdings_text = '**Top holdings:**\n' + '\n'.join(
                    f"- {a['stock_symbol']}: {a['allocation_percent']:.1f}% of portfolio"
                    for a in allocation[:5]
                )

            return FALLBACK_TEMPLATES['summary'].format(
                holdings_count=summary['holdings_count'],
                total_invested=summary['total_invested'],
                total_current=summary['total_current_value'],
                total_pnl=summary['total_pnl'],
                pnl_percent=summary['pnl_percent'],
                top_holdings=top_holdings_text,
            )

        if analysis_type == 'risk':
            top_alloc = allocation[0]['allocation_percent'] if allocation else 0
            concentration = 'High' if top_alloc > 30 else ('Moderate' if top_alloc > 15 else 'Low')
            diversified = (
                'Well diversified across multiple holdings'
                if summary['holdings_count'] >= 10
                else 'Consider adding more holdings for better diversification'
            )

            return FALLBACK_TEMPLATES['risk'].format(
                concentration_status=concentration,
                holdings_count=summary['holdings_count'],
                top_allocation=top_alloc,
                diversification_note=diversified,
            )

        if analysis_type == 'allocation':
            breakdown = '\n'.join(
                f"- **{a['stock_symbol']}**: {a['allocation_percent']:.1f}% "
                f"(₹{a['invested_value']:,.2f})"
                for a in allocation[:10]
            )
            return FALLBACK_TEMPLATES['allocation'].format(
                allocation_breakdown=breakdown or 'No allocation data available.',
            )

        return 'Analysis type not supported. Try: summary, risk, allocation, or recommendation.'
