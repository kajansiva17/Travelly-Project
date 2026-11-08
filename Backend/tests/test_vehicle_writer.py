import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text
from app.services.review_audit import AuditJournal
from app.core.errors import ApiError
from test_vehicles import actors,submitted,call


def test_separate_writer_projects_only_owned_latest_feedback_without_history_access(client,actors,tmp_path,monkeypatch):
    a=actors;row=submitted(client,a)
    rejected=call(client,a,'admin','patch',f"/admin/vehicles/{row['id']}/review",{'expected_version':row['version'],'decision':'REJECTED','reason':'Correct the submitted vehicle specification.'})
    assert rejected.status_code==200
    offline=client.app.state.audit
    key=tmp_path/'vehicle-ipc.key';key.write_bytes(secrets.token_bytes(32))
    endpoint='\\\\.\\pipe\\TravellyReviewAudit-'+uuid4().hex if os.name=='nt' else str(tmp_path/'vehicle.sock')
    settings=client.app.state.settings.model_copy(update={'review_audit_endpoint':endpoint,'review_audit_auth_file':key})
    with client.app.state.engine.connect() as db:schema=db.scalar(text('select current_schema()'))
    env={**os.environ,'REVIEW_AUDIT_ENDPOINT':endpoint,'REVIEW_AUDIT_AUTH_FILE':str(key),'REVIEW_AUDIT_ROOT':str(settings.review_audit_root),
        'REVIEW_DATABASE_IDENTITY':settings.review_database_identity,'TEST_SCHEMA':schema}
    script="""
import os
from app.core.config import get_settings
from app.dependencies.database import make_engine
from app.services.review_audit import FileAuditJournal
from app.services.review_writer import serve
s=get_settings();e=make_engine(s.database_url,connect_args={'options':'-csearch_path='+os.environ['TEST_SCHEMA']+',public'})
serve(s,FileAuditJournal(s,e))
"""
    writer_log=(tmp_path/'vehicle-writer.log').open('w',encoding='utf8')
    process=subprocess.Popen([sys.executable,'-c',script],cwd=Path(__file__).parents[1],env=env,stdout=writer_log,stderr=writer_log,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    remote=AuditJournal(settings,client.app.state.engine)
    try:
        for _ in range(300):
            if process.poll() is not None:
                writer_log.flush()
                raise AssertionError('Vehicle projection writer exited: '+(tmp_path/'vehicle-writer.log').read_text(encoding='utf8'))
            try:
                with remote.coordinated():pass
                break
            except ApiError:time.sleep(.1)
        else:raise AssertionError('Vehicle projection writer did not start.')
        client.app.state.audit=remote
        def forbidden(*args):raise AssertionError('Web runtime cannot read journal/key files.')
        monkeypatch.setattr(remote,'root',forbidden)
        result=call(client,a,'owner','get','/owners/me/vehicles/'+row['id'])
        assert result.status_code==200,result.text
        assert result.json()['registration_locked'] and result.json()['latest_decision']['reason']=='Correct the submitted vehicle specification.'
        from datetime import datetime, timedelta, timezone
        start=datetime.now(timezone.utc)+timedelta(days=2)
        payload={'kind':'MAINTENANCE','start_at':start.isoformat(),'end_at':(start+timedelta(hours=2)).isoformat(),'reason':'Planned inspection'}
        path=f"/vehicles/{row['id']}/availability-blocks"
        created=call(client,a,'owner','post',path,payload)
        assert created.status_code==201,created.text
        bid=created.json()['id']
        edited=call(client,a,'owner','patch',path+'/'+bid,{**payload,'expected_version':1,'reason':'Updated inspection plan'})
        assert edited.status_code==200,edited.text
        withdrawn=call(client,a,'owner','post',path+'/'+bid+'/withdraw',{'expected_version':2,'reason':'Inspection completed elsewhere'})
        assert withdrawn.status_code==200 and withdrawn.json()['withdrawn']
        evidence=[e for e in offline.records()[0] if e.get('outcome')=='committed' and e.get('target',{}).get('id')==bid]
        assert len(evidence)==3 and evidence[1]['previous_decision_evidence']['before']['reason']=='Planned inspection'
        assert evidence[1]['previous_decision_evidence']['after']['reason']=='Updated inspection plan'
        with pytest.raises(ApiError):remote.records()
        with pytest.raises(ApiError):
            with remote.coordinated():remote.vehicle_projection(a['other']['id'],row['id'])
        process.kill();process.wait(timeout=5)
        assert call(client,a,'owner','get','/owners/me/vehicles/'+row['id']).status_code==503
        assert call(client,a,'owner','post',path,payload).status_code==503
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=5)
        writer_log.close()
        client.app.state.audit=offline
