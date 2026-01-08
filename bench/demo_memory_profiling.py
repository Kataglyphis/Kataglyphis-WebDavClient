from memory_profiler import profile
from kataglyphis_webdavclient.dummy import SimpleMLPreprocessor


@profile
def test_memory_profile():
    ml = SimpleMLPreprocessor(1000)
    ml.run_pipeline()


test_memory_profile()
