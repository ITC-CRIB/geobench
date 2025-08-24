import argparse
import math
import multiprocessing
import time


def count_primes(n):
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(math.sqrt(i)) + 1)):
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Count primes in parallel.")
    parser.add_argument(
        '-c', '--cores', type=int,
        default=multiprocessing.cpu_count() // 2,
        help="Number of CPU cores to use (default: half of available cores)"
    )
    parser.add_argument(
        '--n', '--num', type=int,
        default=1_000_000,
        help="Number to check primes up to (default: 1_000_000)"
    )
    args = parser.parse_args()

    print(f"Using {args.cores} cores, checking numbers up to {args.n}.")

    start_time = time.time()

    with multiprocessing.Pool(args.cores) as pool:
        results = pool.map(count_primes, [args.n] * args.cores)

    total_primes = sum(results)
    end_time = time.time()

    print(f"Total primes counted: {total_primes}")
    print(f"Elapsed time: {end_time - start_time:.2f} s.")


if __name__ == "__main__":
    main()
