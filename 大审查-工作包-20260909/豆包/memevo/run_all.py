# -*- coding: utf-8 -*-
"""run_all.py — 一键复现：基线探针 + 十二轮 78 实验（E1-E60、E64-E66、E70-E79；含 E22b/E22c/E24b）。纯标准库。
用法（PowerShell）: python run_all.py > results_all.txt 2>&1 ; 或直接 python run_all.py"""
import subprocess, sys, time, os
HERE=os.path.dirname(os.path.abspath(__file__))
MODS=["baseline_review.py","exp_round1.py","exp_round2.py","exp_round3.py",
      "exp_round4.py","exp_round5.py","exp_round6.py","exp_round7.py","exp_round8.py",
      "exp_round9.py","exp_round10.py","exp_round11.py","exp_round12.py"]
def main():
    t0=time.time()
    for m in MODS:
        print("\n"+"#"*84); print("# 运行模块:",m); print("#"*84)
        r=subprocess.run([sys.executable,"-X","utf8",os.path.join(HERE,m)],
                         capture_output=True,text=True,encoding="utf-8",errors="replace")
        print(r.stdout)
        if r.returncode!=0:
            print("[FATAL]",m,"exit",r.returncode); print(r.stderr); sys.exit(1)
    print("\n"+"="*84); print(f"全部模块运行成功，总用时 {time.time()-t0:.1f}s，exit 0"); print("="*84)
if __name__=="__main__":
    main()
