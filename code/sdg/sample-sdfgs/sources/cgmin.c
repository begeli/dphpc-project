static void conj_grad (
    int colidx[],
    int rowstr[],
    double x[],
    double z[],
    double a[],
    double p[],
    double q[],
    double r[],

    double *rnorm,int firstrow,int lastrow,int firstcol,int lastcol )

{
    static int callcount = 0;
    double d, sum, rho, rho0, alpha, beta;
    //int cgit,i, j, k;
    int  cgitmax = 25;

    rho = 0.0;

    for (int j = 1; j <= naa+1; j++) {
 q[j] = 0.0;
 z[j] = 0.0;
 r[j] = x[j];
 p[j] = r[j];

    }


    for (int j = 1; j <= lastcol-firstcol+1; j++) {
 rho = rho + r[j]*r[j];
    }

    for (int cgit = 1; cgit <= cgitmax; cgit++) {
      rho0 = rho;
      d = 0.0;
      rho = 0.0;


 for (int j = 1; j <= lastrow-firstrow+1; j++) {
            sum = 0.0;
     for (int k = rowstr[j]; k < rowstr[j+1]; k++) {
  sum = sum + a[k]*p[colidx[k]];
     }

            q[j] = sum;
 }

 for (int j = 1; j <= lastcol-firstcol+1; j++) {
            d = d + p[j]*q[j];
 }

 alpha = rho0 / d;

 for (int j = 1; j <= lastcol-firstcol+1; j++) {
            z[j] = z[j] + alpha*p[j];
            r[j] = r[j] - alpha*q[j];

            rho = rho + r[j]*r[j];
 }

 beta = rho / rho0;

 for (int j = 1; j <= lastcol-firstcol+1; j++) {
            p[j] = r[j] + beta*p[j];
 }
    callcount++;
    }

    sum = 0.0;

    for (int j = 1; j <= lastrow-firstrow+1; j++) {
 d = 0.0;
 for (int k = rowstr[j]; k <= rowstr[j+1]-1; k++) {
            d = d + a[k]*z[colidx[k]];
 }
 r[j] = d;
    }


    for (int j = 1; j <= lastcol-firstcol+1; j++) {
 d = x[j] - r[j];
 sum = sum + d*d;
    }

    (*rnorm) = sqrt(sum);
}


int main() {
    //int  it;
    int nthreads = 1;
    double zeta;
    double rnorm;
    double norm_temp11;
    double norm_temp12;
    double t, mflops;
    char classa;
    int verified;
    double zeta_verify_value, epsilon;


static int naa;
static int nzz;
static int firstrow;
static int lastrow;
static int firstcol;
static int lastcol;


static int colidx[1400*(7 +1)*(7 +1)+1400*(7 +2)+1];
static int rowstr[1400 +1+1];
static int iv[2*1400 +1+1];
static int arow[1400*(7 +1)*(7 +1)+1400*(7 +2)+1];
static int acol[1400*(7 +1)*(7 +1)+1400*(7 +2)+1];


static double v[1400 +1+1];
static double aelt[1400*(7 +1)*(7 +1)+1400*(7 +2)+1];
static double a[1400*(7 +1)*(7 +1)+1400*(7 +2)+1];
static double x[1400 +2+1];
static double z[1400 +2+1];
static double p[1400 +2+1];
static double q[1400 +2+1];
static double r[1400 +2+1];

static double amult;
static double tran;

    firstrow = 1;
    lastrow = 1400;
    firstcol = 1;
    lastcol = 1400;


    naa = 1400;
    nzz = 1400*(7 +1)*(7 +1)+1400*(7 +2);




    tran = 314159265.0;
    amult = 1220703125.0;
    zeta = 42.0;





    for (int it = 1; it <= 15; it++) {




 conj_grad(colidx, rowstr, x, z, a, p, q, r , &rnorm,firstrow,lastrow,firstcol,lastcol);


 norm_temp11 = 0.0;
 norm_temp12 = 0.0;

 for (int j = 1; j <= lastcol-firstcol+1; j++) {
            norm_temp11 = norm_temp11 + x[j]*z[j];
            norm_temp12 = norm_temp12 + z[j]*z[j];
 }

 norm_temp12 = 1.0 / sqrt( norm_temp12 );

 zeta = 10.0 + 1.0 / norm_temp11;


 for (int j = 1; j <= lastcol-firstcol+1; j++) {
            x[j] = norm_temp12*z[j];
 }
    }

}

