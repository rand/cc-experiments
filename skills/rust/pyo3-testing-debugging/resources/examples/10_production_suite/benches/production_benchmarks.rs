use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use production_suite::compute;

fn bench_statistics(c: &mut Criterion) {
    let sizes = [100, 1_000, 10_000, 100_000];

    let mut group = c.benchmark_group("statistics");
    for size in sizes.iter() {
        let data: Vec<f64> = (0..*size).map(|x| x as f64).collect();

        group.bench_with_input(BenchmarkId::new("sum", size), size, |b, _| {
            b.iter(|| compute::sum(black_box(&data)))
        });

        group.bench_with_input(BenchmarkId::new("mean", size), size, |b, _| {
            b.iter(|| compute::mean(black_box(&data)))
        });

        group.bench_with_input(BenchmarkId::new("variance", size), size, |b, _| {
            b.iter(|| compute::variance(black_box(&data)))
        });

        group.bench_with_input(BenchmarkId::new("std_dev", size), size, |b, _| {
            b.iter(|| compute::std_dev(black_box(&data)))
        });
    }
    group.finish();
}

criterion_group!(benches, bench_statistics);
criterion_main!(benches);
