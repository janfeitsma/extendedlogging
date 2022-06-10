
import extendedlogging
import multiprocessing
import threading
import time



SLEEP_TIME = 0.1
NUM_THREADS = 2
NUM_PROCESSES = 3


@extendedlogging.traced
def doit_thread():
    time.sleep(SLEEP_TIME)
    #extendedlogging.info('thread {} in process {} is done'.format(threading.current_thread().name, multiprocessing.current_process()))


@extendedlogging.traced
def doit_process():
    threads = []
    for it in range(NUM_THREADS):
        threads.append(threading.Thread(target=doit_thread))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    #extendedlogging.info('process {} is done'.format(multiprocessing.current_process()))

@extendedlogging.traced
def main():
    processes = [multiprocessing.Process(target=doit_process) for x in range(NUM_PROCESSES)]
    for p in processes:
        p.start()
    for p in processes:
        p.join()


if __name__ == "__main__":
    extendedlogging.configure(tracing=True, thread_names=True, process_names=True)
    main()

