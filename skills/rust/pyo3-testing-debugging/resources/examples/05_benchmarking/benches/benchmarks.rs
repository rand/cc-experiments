use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use benchmarking::{internal_sum, internal_factorial, internal_fibonacci};

fn bench_sum(c: &mut Criterion) {
    let sizes = [100, 1_000, 10_000, 100_000];

    let mut group = c.benchmark_group("sum");
    for size in sizes.iter() {
        let data: Vec<f64> = (0..*size).map(|x| x as f64).collect();
        group.bench_with_input(BenchmarkId::from_parameter(size), size, |b, _| {
            b.iter(|| internal_sum(black_box(&data)))
        });
    }
    group.finish();
}

fn bench_factorial(c: &mut Criterion) {
    c.bench_function("factorial_20", |b| {
        b.iter(|| internal_factorial(black_box(20)))
    });
}

fn bench_fibonacci(c: &mut Criterion) {
    let mut group = c.benchmark_group("fibonacci");
    for n in [10u32, 20, 30, 40].iter() {
        group.bench_with_input(BenchmarkId::from_parameter(n), n, |b, &n| {
            b.iter(|| internal_fibonacci(black_box(n)))
        });
    }
    group.finish();
}

criterion_group!(benches, bench_sum, bench_factorial, bench_fibonacci);
criterion_main!(benches);
