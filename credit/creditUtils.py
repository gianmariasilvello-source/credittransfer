'''
Utility function to display results from GeneralCreditTransfer computations.
'''
def display_results(ct, total_credit, kudos, diagnostics):
    # Display results
    print(f"\nSpectral radius: {diagnostics['spectral_radius']:.6f}")
    print(f"Converges: {diagnostics['converges']}")
    print(f"\nResults:")
    results = ct.get_results_dict(total_credit, kudos)
    for node in sorted(results.keys()):
        print(f"  {node}: total_credit={results[node]['total_credit']:.4f}, "
              f"kudos={results[node]['kudos']:.4f}")

    print(f"\nConservation check:")
    print(f"  Total kudos: {diagnostics['total_kudos']:.6f}")
    print(f"  Total edges: {diagnostics['total_external_credit']:.6f}")
    print(f"  Error: {diagnostics['conservation_error']:.10e}")


"""
Utility function to perform full conservation check and print node-level overview.
"""


# python
def report_conservation_and_nodes(ct, total_credit, kudos, verbose=False):
    """
    Runs verification of the conservation property with detailed report,
    then prints node-level total credit and kudos, and summary status.

    Args:
        ct: An instance of GeneralCreditTransfer
        verbose: bool or string-like (e.g. 'false', 'Falso') indicating verbosity
    """
    # Normalize verbose to a boolean (accepts common string variants)
    if isinstance(verbose, str):
        v = verbose.strip().lower()
        false_vals = {'false', 'f', 'no', 'n', '0', 'falso'}
        verbose_flag = False if v in false_vals else True
    else:
        verbose_flag = bool(verbose)

    # Verify conservation with detailed report
    conservation = ct.verify_conservation(total_credit, kudos, verbose_flag)

    # Display node-level results
    print("\nNode-level results:")
    results = ct.get_results_dict(total_credit, kudos)
    for node in sorted(results.keys()):
        tc = results[node]['total_credit']
        k = results[node]['kudos']
        print(f"  {node}: total_credit={tc:.4f}, kudos={k:.4f}")

    # Summary status
    if conservation.get('verified', False):
        print("\n✓ All checks passed!")
    else:
        err = conservation.get('error', 0.0)
        print(f"\n✗ Conservation failed with error {err:.2e}")
