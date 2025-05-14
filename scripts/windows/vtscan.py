# Copyright © 2019 The vt-py authors. All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shows how to upload files to VT using vt-py."""

import asyncio
import itertools
import os
import sys

import vt


async def get_files_to_upload(queue, path):
  """Finds which files will be uploaded to VirusTotal."""
  files = path.split(',')
  for f in files:
    await queue.put(f)
  return len(files)


async def upload_hashes(queue, apikey):
  """Uploads selected files to VirusTotal."""
  return_values = []

  async with vt.Client(apikey) as client:
    while not queue.empty():
      file_path = await queue.get()
      with open(file_path, 'rb') as f:
        analysis = await client.scan_file_async(file=f)
        print(f"File {file_path} uploaded.")
        queue.task_done()
        return_values.append((analysis, file_path))

  return return_values


async def process_analysis_results(apikey, analysis, file_path):
  async with vt.Client(apikey) as client:
    completed_analysis = await client.wait_for_analysis_completion(analysis)
    print(f"{file_path}: {completed_analysis.stats}")
    print(f"analysis id: {completed_analysis.id}")


async def main(key: str, path: str):
  queue = asyncio.Queue()
  n_files = await get_files_to_upload(queue, path)

  worker_tasks = []
  for _ in range(min(4, n_files)):
    worker_tasks.append(asyncio.create_task(upload_hashes(queue, key)))

  # Wait until all worker tasks has completed.
  analyses = itertools.chain.from_iterable(await asyncio.gather(*worker_tasks))
  await asyncio.gather(
      *[
          asyncio.create_task(process_analysis_results(key, a, f))
          for a, f in analyses
      ]
  )


if __name__ == '__main__':
    env_key = os.environ.get('VTCLI_APIKEY')
    asyncio.run(main(env_key, sys.argv[1]))
