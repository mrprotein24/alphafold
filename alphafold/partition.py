from partition_helpers import *

# Four parameter model
Kd_BP  = 0.001;
C_init = 2          # a bit like exp(a) in multiloop
l      = 0.5        # a bit like exp(b) in multiloop
l_BP   = 0.1        # a bit like exp(c) in multiloop
params_default = [ Kd_BP, C_init, l, l_BP ]
C_std = 1; # 1 M. drops out in end (up to overall scale factor).

def partition( sequences, params = params_default, verbose = False, circle = False ):

    # unwrap the parameters of the model
    Kd_BP  = params[0]
    C_init = params[1]
    l      = params[2]
    l_BP   = params[3]
    C_init_BP = C_init * (l_BP/l) # 0.2
    min_loop_length = 1

    ( sequence, is_cutpoint, any_cutpoint ) = initialize_sequence_information( sequences, circle )
    ( Z_BP, C_eff, Z_linear, dZ_BP, dC_eff, dZ_linear ) = initialize_dynamic_programming_matrices( len( sequence ), C_init )
    N = len( sequence )

    # do the dynamic programming
    # deriv calculations are making this long and messy; this should be simplifiable
    for offset in range( 1, N ): #length of subfragment
        for i in range( N ): #index of subfragment
            j = (i + offset) % N;  # N cyclizes
            update_Z_BP( (i,j), sequence, C_std, l, l_BP, Kd_BP, is_cutpoint, any_cutpoint, min_loop_length, Z_BP, C_eff, Z_linear, dZ_BP, dC_eff, dZ_linear )

            if not is_cutpoint[(j-1) % N]:
                C_eff[i][j]  += C_eff[i][(j-1) % N] * l
                dC_eff[i][j] += dC_eff[i][(j-1) % N] * l

            C_eff[i][j]  += C_init_BP * Z_BP[i][j]
            dC_eff[i][j] += C_init_BP * dZ_BP[i][j]

            for k in range( i+1, i+offset):
                if not is_cutpoint[ (k-1) % N]:
                    C_eff[i][j]  += C_eff[i][(k-1) % N] * Z_BP[k % N][j] * l_BP
                    dC_eff[i][j] += ( dC_eff[i][(k-1) % N] * Z_BP[k % N][j] + C_eff[i][(k-1) % N] * dZ_BP[k % N][j] ) * l_BP

            if not is_cutpoint[(j-1) % N]:
                Z_linear[i][j]  += Z_linear[i][(j - 1) % N]
                dZ_linear[i][j] += dZ_linear[i][(j - 1) % N]

            Z_linear[i][j]  += Z_BP[i][j]
            dZ_linear[i][j] += dZ_BP[i][j]

            for k in range( i+1, i+offset):
                if not is_cutpoint[ (k-1) % N]:
                    Z_linear[i][j]  += Z_linear[i][(k-1) % N] * Z_BP[k % N][j]
                    dZ_linear[i][j] += ( dZ_linear[i][(k-1) % N] * Z_BP[k % N][j] + Z_linear[i][(k-1) % N] * dZ_BP[k % N][j] )

    # get the answer (in N ways!)
    Z_final  = []
    dZ_final = []
    for i in range( N ):
        Z_final.append( 0 )
        dZ_final.append( 0 )

        if is_cutpoint[(i + N - 1) % N]:
            Z_final[i]  += Z_linear[i][(i-1) % N]
            dZ_final[i] += dZ_linear[i][(i-1) % N]
        else:
            # Scaling Z_final by Kd_lig/C_std to match previous literature conventions
            Z_final[i]  += C_eff[i][(i - 1) % N] * l / C_std
            dZ_final[i] += dC_eff[i][(i - 1) % N] * l / C_std

            for c in range( i, i + N - 1):
                if is_cutpoint[c % N]:
                    #any split segments, combined independently
                    Z_final[i]  += Z_linear[i][c % N] * Z_linear[(c+1) % N][ i - 1 ]
                    dZ_final[i] += ( dZ_linear[i][c % N] * Z_linear[(c+1) % N][ i - 1 ] + Z_linear[i][c % N] * dZ_linear[(c+1) % N][ i - 1 ] )


    # base pair probability matrix
    bpp = initialize_zero_matrix( N );
    bpp_tot = 0.0
    for i in range( N ):
        for j in range( N ):
            bpp[i][j] = Z_BP[i][j] * Z_BP[j][i] * Kd_BP * (l_BP / l) / Z_final[0]
            bpp_tot += bpp[i][j]/2.0 # to avoid double counting (i,j) and (j,i)

    if verbose:
        output_DP( "Z_BP", Z_BP )
        output_DP( "C_eff", C_eff, Z_final )
        output_DP( "Z_linear", Z_linear )
        output_square( "BPP", bpp );


    # stringent test that partition function is correct -- all the Z(i,i) agree.
    for i in range( N ):
        assert( abs( ( Z_final[i] - Z_final[0] ) / Z_final[0] ) < 1.0e-5 )
        assert( abs( ( dZ_final[i] - dZ_final[0] ) / dZ_final[0] ) < 1.0e-5 )

    # calculate bpp_tot = -dlog Z_final /dlog Kd_BP in two ways! wow cool test
    bpp_tot_based_on_deriv = -dZ_final[0] * Kd_BP / Z_final[0]
    assert( abs( ( bpp_tot - bpp_tot_based_on_deriv )/bpp_tot ) < 1.0e-5 )

    print 'sequence =', sequence
    cutpoint = ''
    for i in range( N ):
        if is_cutpoint[ i ]: cutpoint += 'X'
        else: cutpoint += ' '
    print 'cutpoint =', cutpoint
    print 'circle   = ', circle
    print 'Z =',Z_final[0]

    return ( Z_final[0], bpp, dZ_final[0] )