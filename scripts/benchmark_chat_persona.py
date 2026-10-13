"""Local resolver benchmark with a real temporary manifest; no network or keys."""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psutil
from pet.chat.models import ChatSettings
from pet.chat.prompt import PromptBuilder


def main():
    # The explicit review base is local Git history, never a network fetch.
    source = subprocess.check_output(['git', 'show', '8c4d21b:pet/chat/prompt.py'], text=True)
    old = {'__name__': 'pet.chat.persona_benchmark_base', '__package__': 'pet.chat'}
    exec(compile(source, '8c4d21b:pet/chat/prompt.py', 'exec'), old)
    result = {'samples_per_case': 20000}
    with tempfile.TemporaryDirectory(prefix='pet-persona-benchmark-') as directory:
        root = Path(directory)
        (root/'role').mkdir()
        (root/'role'/'manifest.json').write_text(json.dumps({'chat': {'system_prompt': 'PACKAGED-ROLE'}}), encoding='utf-8')
        before, after = old['PromptBuilder'](root), PromptBuilder(root)
        process = psutil.Process()
        result['rss_before_mib'] = process.memory_info().rss/1024**2
        for custom in (False, True):
            settings = ChatSettings.defaults()
            if custom:
                settings.default_system_prompt = 'SYNTHETIC-USER-PERSONA'
            for label, builder in [('base', before), ('current', after)]:
                start = time.perf_counter()
                for _ in range(20000):
                    actual = builder.effective_system_prompt(settings, 'role')
                result[('custom' if custom else 'default')+'_'+label+'_us'] = (time.perf_counter()-start)*1e6/20000
                assert actual == ('SYNTHETIC-USER-PERSONA' if custom and label == 'current' else 'PACKAGED-ROLE')
        result['rss_after_mib'] = process.memory_info().rss/1024**2
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
