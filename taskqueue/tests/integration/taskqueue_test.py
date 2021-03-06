# pylint: disable=too-many-locals
import json
import uuid

import aiohttp
import pytest
from gcloud.aio.taskqueue import decode
from gcloud.aio.taskqueue import encode
from gcloud.aio.taskqueue import TaskQueue


@pytest.mark.asyncio
async def test_task_lifecycle(creds, project, task_queue):
    async with aiohttp.ClientSession() as session:
        tq = TaskQueue(project, creds, task_queue, session=session)

        payload = {'this': {'is': {'a': {'test': uuid.uuid4().hex}}}}
        tag = 'smoke-test'

        # DRAIN
        await tq.drain()

        # INSERT
        inserted = await tq.insert(encode(json.dumps(payload)),
                                   tag=encode(tag))
        assert inserted

        # GET
        assert inserted == await tq.get(inserted['name'], full=True)

        # LIST
        listed = await tq.list(full=True)
        assert listed.get('tasks')
        assert inserted in listed['tasks']

        # LEASE
        leased = await tq.lease(num_tasks=1, lease_seconds=10,
                                task_filter=f'tag={encode(tag)}')
        assert leased.get('tasks') and len(leased['tasks']) == 1

        leased_message = leased['tasks'][0]['pullMessage']
        assert payload == json.loads(decode(leased_message['payload']))
        assert tag == decode(leased_message['tag'])

        # RENEW
        renewed = await tq.renew(leased['tasks'][0], lease_seconds=10)
        for k, v in renewed.items():
            if k == 'scheduleTime':
                assert v != leased['tasks'][0][k]
            else:
                assert v == leased['tasks'][0][k]

        # ack?
        # cancel?

        # DELETE
        assert not await tq.delete(renewed['name'])
