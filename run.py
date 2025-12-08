import runpy

if __name__ == "__main__":
    # app.main 모듈을 메인 프로그램으로 실행
    runpy.run_module('app.main', run_name="__main__")