import lightbulb

loader = lightbulb.Loader()
ticket = lightbulb.Group("ticket", "Manual ticket management commands")

__all__ = ["loader", "ticket"]