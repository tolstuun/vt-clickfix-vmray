from apscheduler.schedulers.asyncio import AsyncIOScheduler


def make_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler()


def attach_jobs(scheduler: AsyncIOScheduler, app) -> None:
    from app.config import settings

    if not settings.pipeline_autostart:
        return

    from app.services.pipeline import VTPipeline, URLProcessPipeline, VMRaySubmitPipeline, VMRayPollPipeline

    async def _vt_poll():
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(app.state.db_engine) as session:
            result = await VTPipeline(session, app.state.vt_client).run()
            url_result = await URLProcessPipeline(session).run()
        return result, url_result

    async def _vmray_submit():
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(app.state.db_engine) as session:
            return await VMRaySubmitPipeline(session, app.state.vmray_client).run()

    async def _vmray_poll():
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(app.state.db_engine) as session:
            return await VMRayPollPipeline(session, app.state.vmray_client).run()

    if settings.vt_enabled:
        scheduler.add_job(_vt_poll, "interval", seconds=settings.vt_poll_interval_seconds, id="vt_poll")

    if settings.vmray_enabled:
        scheduler.add_job(
            _vmray_submit, "interval", seconds=settings.vmray_poll_interval_seconds, id="vmray_submit"
        )
        scheduler.add_job(
            _vmray_poll, "interval", seconds=settings.vmray_poll_interval_seconds, id="vmray_poll"
        )
