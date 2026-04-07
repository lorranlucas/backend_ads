from fastapi import Query, Request
from typing import Optional, List, Tuple
from datetime import datetime, timedelta, date

class DashboardFilterParams:
    def __init__(
        self,
        period: str = Query("30dias"),
        start_date: Optional[str] = Query(None),
        end_date: Optional[str] = Query(None),
        platform: str = Query("all"),
        client_ids: Optional[str] = Query(None),
        campaign_ids: Optional[str] = Query(None)
    ):
        # Resilience: if start_date is provided, the intent is almost always 'custom'
        if start_date and period != "custom":
            self.period = "custom"
        else:
            self.period = period
            
        self.start_date_str = start_date
        self.end_date_str = end_date
        self.platform = platform
        
        self.client_ids = [c.strip() for c in client_ids.split(",")] if client_ids else []
        self.campaign_ids = [c.strip() for c in campaign_ids.split(",")] if campaign_ids else []

    def get_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Returns start_date, end_date based on period."""
        today = date.today()
        start = None
        end = datetime.combine(today, datetime.max.time())
        end_date_only = today
        
        if self.period == "hoje":
            start = today
        elif self.period == "ontem":
            start = today - timedelta(days=1)
            end_date_only = start
            end = datetime.combine(start, datetime.max.time())
        elif self.period == "7dias":
            start = today - timedelta(days=6)
        elif self.period == "14dias":
            start = today - timedelta(days=13)
        elif self.period == "30dias":
            start = today - timedelta(days=29)
        elif self.period == "semanaAtual":
            start = today - timedelta(days=today.weekday()) # Monday of current week
        elif self.period == "mesAtual":
            start = today.replace(day=1)
        elif self.period == "custom" and self.start_date_str:
            try:
                start = datetime.fromisoformat(self.start_date_str.replace("Z", "+00:00")).date()
                if self.end_date_str:
                    end_date_only = datetime.fromisoformat(self.end_date_str.replace("Z", "+00:00")).date()
                    end = datetime.combine(end_date_only, datetime.max.time())
                else:
                    end_date_only = start
                    end = datetime.combine(start, datetime.max.time())
            except ValueError:
                pass

        start_dt = datetime.combine(start, datetime.min.time()) if start else None
        return start_dt, end

    def apply_to_query(self, query, ad_account_model, ad_insight_model=None, ad_campaign_model=None):
        """Applies filters to an SQLAlchemy query assuming AdAccount and optionally AdInsight/AdCampaign are joined."""
        
        # Filter Platform
        if self.platform != "all":
            query = query.filter(ad_account_model.platform.ilike(self.platform))
            
        # Filter Client IDs (which correspond to AdAccount.id in the backend)
        if self.client_ids:
            query = query.filter(ad_account_model.id.in_(self.client_ids))
            
        # Filter Campaign IDs
        if self.campaign_ids and ad_campaign_model:
            query = query.filter(ad_campaign_model.id.in_(self.campaign_ids))
            
        # Filter Date Range
        if ad_insight_model:
            start_dt, end_dt = self.get_date_range()
            if start_dt:
                query = query.filter(ad_insight_model.date >= start_dt.date())
            if end_dt:
                query = query.filter(ad_insight_model.date <= end_dt.date())
                
        return query
