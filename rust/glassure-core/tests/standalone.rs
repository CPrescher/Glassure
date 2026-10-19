use glassure_core::{
    functions as f,
    parallel::{Executor, Item, Job},
    pattern::Pattern,
    request::{calculate, Request},
    scattering::{Composition, Source},
};

#[test]
fn pattern_io_arithmetic_and_missing_bins() {
    let p = Pattern::from_xy_text("# measured\n0 1\n1 2\n2 4\n3 8\n", 0).unwrap();
    assert_eq!(p.x, vec![0., 1., 2., 3.]);
    let q = Pattern::from_xy_text(&p.to_xy_text().unwrap(), 0).unwrap();
    assert_eq!(p.y, q.y);
    let b = Pattern::new(vec![0., 1.5, 3.], vec![2.; 3]).unwrap();
    assert_eq!(p.combine(&b, -1.).unwrap().y, vec![-1., 0., 2., 6.]);
    assert_eq!(
        p.extend_to(-2., 0.).unwrap().x,
        vec![-2., -1., 0., 1., 2., 3.]
    );
    assert!(p.rebin(0.25).unwrap().y.iter().any(|v| v.is_nan()));
    assert!(p.smooth(-1.).is_err());
    assert!(p.rebin(0.).is_err());
}
#[test]
fn analytic_transforms_and_density_roundtrip() {
    let q: Vec<_> = (0..101).map(|i| i as f64 * 0.1).collect();
    let p = Pattern::new(q, vec![1.; 101]).unwrap();
    let r: Vec<_> = (0..201).map(|i| i as f64 * 0.01).collect();
    for method in [glassure_core::Method::Integral, glassure_core::Method::Fft] {
        let fr = f::calculate_fr(&p, &r, method, true).unwrap();
        assert!(fr.y.iter().all(|v| *v == 0.));
        assert!(f::calculate_gr(&fr, 0.066)
            .unwrap()
            .y
            .iter()
            .all(|v| *v == 1.));
    }
    let c = Composition::Formula(" Mg2 [SiO4] ".into());
    let rho = glassure_core::scattering::atomic_density(&c, 2.9).unwrap();
    assert!((glassure_core::scattering::mass_density(&c, rho).unwrap() - 2.9).abs() < 1e-14);
}
#[test]
fn full_rust_pipeline_and_ordered_multicore() {
    let x: Vec<_> = (1..501).map(|i| i as f64 * 0.04).collect();
    let c = Composition::Formula("SiO2".into());
    let factors =
        glassure_core::scattering::factors_with_source(&c, 2.2, &x, Source::Hajdu).unwrap();
    let intensity = factors
        .f2
        .iter()
        .zip(&factors.incoherent)
        .map(|(a, b)| (a + b) / 2.)
        .collect();
    let p = Pattern::new(x, intensity).unwrap();
    let mut req = Request::new(p, c, 2.2).unwrap();
    req.scattering_factor_source = Source::Hajdu;
    let result = calculate(req.clone()).unwrap();
    assert!((result.normalization - 2.).abs() < 1e-12);
    assert!(
        result
            .sq
            .y
            .iter()
            .filter(|v| (**v - 1.).abs() > 1e-10)
            .count()
            < 10
    );
    let batch = Executor::new(4)
        .unwrap()
        .batch(vec![Job::Calculate(req.clone()); 8])
        .unwrap();
    for item in batch.items {
        let Item::Success { output } = item else {
            panic!("valid job failed")
        };
        let glassure_core::parallel::JobOutput::Calculate(value) = *output else {
            panic!("wrong operation")
        };
        assert_eq!(value.gr.y, result.gr.y);
    }
}
#[test]
fn invalid_standalone_inputs_are_errors() {
    assert!(f::calculate_fr(
        &Pattern {
            x: vec![],
            y: vec![]
        },
        &[0., 1.],
        glassure_core::Method::Fft,
        false
    )
    .is_err());
    assert!(glassure_core::numeric::polynomial_origin(&[1., 2.], &[1.], 2).is_err());
    assert!(glassure_core::sq_optimization::optimize(
        &[],
        &[],
        1.,
        0.01,
        glassure_core::Method::Fft,
        &glassure_core::SqOptimization {
            method: "fit".into(),
            r_cutoff: 1.,
            iterations: 1,
            lorch: false,
            attenuation: 1.
        }
    )
    .is_err());
}
#[test]
fn zero_container_predictor_has_finite_coefficients() {
    let x: Vec<_> = (1..101).map(|i| i as f64 * 0.1).collect();
    let f2: Vec<_> = x.iter().map(|x| 2. + x * x).collect();
    let p = Pattern::new(x, f2.iter().map(|v| (v + 3.) / 2.3).collect()).unwrap();
    let (params, _) = f::normalize_fit(&p, &f2, None, 3., "squared", true, None).unwrap();
    assert!(params.n_container.abs() < 1e-10);
    assert!((params.n - 2.3).abs() < 1e-10);
    assert!((params.multiple - 3.).abs() < 1e-10);
}
#[test]
fn transforms_accept_the_legacy_extrapolated_zero_endpoint() {
    use glassure_core::{functions, pattern::Pattern, Method};
    let mut q: Vec<_> = (0..101).map(|i| i as f64 * 0.1).collect();
    let y: Vec<_> = q.iter().map(|q| 1. + q.sin()).collect();
    let r: Vec<_> = (0..101).map(|i| 1e-10 + i as f64 * 0.01).collect();
    for method in [Method::Fft, Method::Integral] {
        let exact = Pattern::new(q.clone(), y.clone()).unwrap();
        let expected = functions::calculate_fr(&exact, &r, method, false).unwrap();
        q[0] = -8e-16;
        let rounded = Pattern::new(q.clone(), y.clone()).unwrap();
        let actual = functions::calculate_fr(&rounded, &r, method, false).unwrap();
        for (a, e) in actual.y.iter().zip(&expected.y) {
            assert!((a - e).abs() < 1e-12 * (1. + e.abs()));
        }
        assert_eq!(rounded.x[0], -8e-16);
        q[0] = -0.02;
        let extended = Pattern::new(q.clone(), y.clone()).unwrap();
        let actual = functions::calculate_fr(&extended, &r, method, false).unwrap();
        assert!(actual.y.iter().all(|v| v.is_finite()));
        if matches!(method, Method::Integral) {
            for (i, radius) in r.iter().enumerate() {
                let expected = 2. / std::f64::consts::PI
                    * q.windows(2)
                        .zip(y.windows(2))
                        .map(|(q, y)| {
                            (q[1] - q[0])
                                * (q[0] * (y[0] - 1.) * (q[0] * radius).sin()
                                    + q[1] * (y[1] - 1.) * (q[1] * radius).sin())
                                / 2.
                        })
                        .sum::<f64>();
                assert!((actual.y[i] - expected).abs() < 1e-12 * (1. + expected.abs()));
            }
        }
        q[0] = -0.3;
        let negative = Pattern::new(q.clone(), y.clone()).unwrap();
        assert!(functions::calculate_fr(&negative, &r, method, false).is_err());
        q[0] = 0.;
    }
}
