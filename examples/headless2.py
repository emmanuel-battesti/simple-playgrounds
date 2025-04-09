import time
from multiprocessing import Process, Manager


def run_environment(headless):
    start_time = time.time()  # Démarre le chronomètre
    if headless:
        import pyglet
        pyglet.options["headless"] = True

    import random
    import arcade
    from spg.agent import HeadAgent
    from spg.element import Ball
    from spg.playground import Room

    playground = Room(size=(500, 200), background=(23, 23, 21))

    ball = Ball()
    ball.graspable = True
    playground.add(ball, ((200, 0), 0))

    ball = Ball()
    ball.graspable = True
    playground.add(ball, ((200, 40), 0))

    ball = Ball(color=(23, 184, 13))
    ball.graspable = True
    playground.add(ball, ((-200, 40), 0))

    ball = Ball(color=arcade.color.AMETHYST)
    ball.graspable = True
    playground.add(ball, ((-200, 0), 0))

    ball = Ball(color=arcade.color.CYAN)
    ball.graspable = True
    playground.add(ball, ((-200, -40), 0))

    agent = HeadAgent()
    playground.add(agent)

    for _ in range(1000):
        agent_command = {agent: {"forward": random.uniform(0, 1),
                                 "angular": random.uniform(-1, 1)}}

        playground.step(commands=agent_command)

    elapsed_time = time.time() - start_time  # Calcule le temps écoulé
    print(f"Elapsed time for {headless}: {elapsed_time:.2f} seconds")
    return elapsed_time


def worker(headless, time_completions, index):
    try:
        time_completions[index] = run_environment(headless)
    except Exception as e:
        print(f"Error in process {index}: {e}")
        time_completions[index] = 0.0  # Default value in case of failure

if __name__ == "__main__":
    hl = [True, False, True, False, True, True, False, False, True, True]

    with Manager() as manager:
        time_completions = manager.list([0] * len(hl))
        processes = []

        for i, headless in enumerate(hl):
            p = Process(target=worker, args=(headless, time_completions, i))
            processes.append(p)
            p.start()

        for p in processes:
            p.join()

        for i, time_completion in enumerate(time_completions):
            print(f"Result for process {i}: {time_completion}")

        print(f"Computing {len(hl)} environments of 1000 ts in {sum(time_completions):.3f} sec")
