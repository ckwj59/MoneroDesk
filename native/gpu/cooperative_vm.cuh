// XMR cooperative ordered VM. One thread group owns one hash; no instruction reordering.
#ifndef XMR_VM_LANES
#define XMR_VM_LANES 32
#endif
#ifndef XMR_VM_THREADS
#define XMR_VM_THREADS 32
#endif
__global__ void cooperative_vm(const void *entropy,void *states,void *scratch,const void *dataset,
                             void *rounding,RefInstruction *code,unsigned iterations) {
    constexpr unsigned width=XMR_VM_LANES,groups=XMR_VM_THREADS/width;
    const unsigned group=threadIdx.x/width,lane=threadIdx.x%width;
    const unsigned index=blockIdx.x*groups+group;
    const unsigned active_mask=(0xffffffffu>>(32-width))<<(((threadIdx.x%32)/width)*width);
    const uint64_t *input=(const uint64_t*)((const uint8_t*)entropy+index*ENTROPY_SIZE);
    uint8_t *sp=(uint8_t*)scratch+index*(RANDOMX_SCRATCHPAD_L3+64ULL);
#ifdef XMR_VM_CODE_GLOBAL
    auto *decoded=code+index*256;
#else
    __shared__ RefInstruction all_decoded[groups][256];
    auto *decoded=all_decoded[group];
#endif
    int usage[8];
    __shared__ volatile uint64_t all_r[groups][8];
    volatile uint64_t *r=all_r[group];
    __shared__ double all_f[groups][8],all_e[groups][8],all_a[groups][8];
    double *f=all_f[group],*e=all_e[group],*a=all_a[group];
    if(lane<8)r[lane]=0;
    for(unsigned j=0;j<8;++j)usage[j]=-1;
    if(lane<8)a[lane]=getSmallPositiveFloatBits(input[lane]);
    const uint64_t masks[2]={getFloatMask(input[14]),getFloatMask(input[15])};
    if(lane==0)for(int pc=0;pc<256;++pc) {
        const uint64_t raw=input[16+pc];auto &ins=decoded[pc];
        ins.op=refOpcode(raw&255);ins.d=(raw>>8)&7;ins.s=(raw>>16)&7;ins.mod=(raw>>24)&255;
        uint32_t imm=raw>>32;ins.imm=(uint64_t)(int64_t)(int32_t)imm;
        ins.mask=(ins.mod&3) ? (RANDOMX_SCRATCHPAD_L1-8) : (RANDOMX_SCRATCHPAD_L2-8);
        if(ins.op==1||ins.op==3||ins.op==5||ins.op==7||ins.op==9||ins.op==13) {
            if(ins.d==ins.s)ins.mask=RANDOMX_SCRATCHPAD_L3-8;
        }
        if(ins.op==10) {
            if(!imm || !(imm&(imm-1))) ins.op=29;
            else {
                unsigned shift=32-__clz(imm);uint64_t q=(1ULL<<63)/imm,rem=(1ULL<<63)%imm;
                ins.imm=(q<<shift)+((rem<<shift)/imm);
            }
        }
        if(ins.op==26) {
            unsigned shift=(ins.mod>>4)+randomx::ConditionOffset;
            ins.target=usage[ins.d];ins.imm|=1ULL<<shift;ins.imm&=~(1ULL<<(shift-1));
            ins.mask=randomx::ConditionMask<<shift;
            for(unsigned j=0;j<8;++j)usage[j]=pc;
        } else if(ins.op<=16) {
            if(ins.op!=16 || ins.d!=ins.s) {
                usage[ins.d]=pc;
                if(ins.op==16)usage[ins.s]=pc;
            }
        }
        if(ins.op==28 && (ins.mod>>4)>=randomx::StoreL3Condition)ins.mask=RANDOMX_SCRATCHPAD_L3-8;
    }
    __syncwarp(active_mask);
    uint32_t ma=input[8]&CacheLineAlignMask,mx=input[10];
    uint64_t address=input[12];const unsigned rr0=address&1,rr1=2+((address>>1)&1),rr2=4+((address>>2)&1),rr3=6+((address>>3)&1);
    const uint8_t *ds=(const uint8_t*)dataset+(input[13]%(randomx::DatasetExtraItems+1))*64;
    uint32_t sp0=mx,sp1=ma,mode=((uint32_t*)rounding)[index];
    for(unsigned iteration=0;iteration<iterations;++iteration) {
        uint64_t mix=r[rr0]^r[rr1];sp0=(sp0^(uint32_t)mix)&ScratchpadL3Mask64;sp1=(sp1^(uint32_t)(mix>>32))&ScratchpadL3Mask64;
        if(lane<8)r[lane]^=*(uint64_t*)(sp+sp0+lane*8);
        if(lane<8) {
            unsigned j=lane;
            f[j]=__int2double_rn(*(int32_t*)(sp+sp1+j*4));
            uint64_t value=__double_as_longlong(__int2double_rn(*(int32_t*)(sp+sp1+32+j*4)));
            e[j]=__longlong_as_double((value&randomx::dynamicMantissaMask)|masks[j&1]);
        }
        __syncwarp(active_mask);
        for(int pc=0;pc<256;++pc) {
            const auto ins=decoded[pc];unsigned d=ins.d,s=ins.s,fd=(d&3)*2,fs=(s&3)*2;
            uint64_t src=r[s],operand=(d==s)?ins.imm:src;
            uint32_t addr=(uint32_t)(src+ins.imm)&ins.mask;
            if(ins.op==1||ins.op==3||ins.op==5||ins.op==7||ins.op==9||ins.op==13)
                operand=*(uint64_t*)(sp+((uint32_t)((d==s?0:src)+ins.imm)&ins.mask));
            if(lane==0 || (lane==1 && ins.op>=18 && ins.op<=25))switch(ins.op) {
            case 0:r[d]+=(src<<((ins.mod>>2)&3))+(d==5?ins.imm:0);break;
            case 1:r[d]+=operand;break;
            case 2:case 3:r[d]-=operand;break;
            case 4:case 5:r[d]*=operand;break;
            case 6:r[d]=__umul64hi(r[d],src);break;
            case 7:r[d]=__umul64hi(r[d],operand);break;
            case 8:r[d]=__mul64hi((int64_t)r[d],(int64_t)src);break;
            case 9:r[d]=__mul64hi((int64_t)r[d],(int64_t)operand);break;
            case 10:r[d]*=ins.imm;break;
            case 11:r[d]=0-r[d];break;
            case 12:case 13:r[d]^=operand;break;
            case 14:r[d]=refRotate(r[d],operand);break;
            case 15:r[d]=refRotate(r[d],0-(unsigned)operand);break;
            case 16:{uint64_t temp=r[d];r[d]=r[s];r[s]=temp;break;}
            case 17:{double *v=d<4?f+d*2:e+(d-4)*2;double temp=v[0];v[0]=v[1];v[1]=temp;break;}
            case 18:case 19:case 20:case 21:
                for(unsigned j=lane;j<2;j+=2) {
                    double v=(ins.op==19||ins.op==21)?__int2double_rn(*(int32_t*)(sp+addr+j*4)):a[fs+j];
                    if(ins.op==20||ins.op==21)v=-v;
                    f[fd+j]=fma_rnd<-1>(f[fd+j],1.0,v,mode);
                }break;
            case 22:for(unsigned j=lane;j<2;j+=2)f[fd+j]=__longlong_as_double(__double_as_longlong(f[fd+j])^0x80f0000000000000ULL);break;
            case 23:for(unsigned j=lane;j<2;j+=2)e[fd+j]=fma_rnd<-1>(e[fd+j],a[fs+j],0.0,mode);break;
            case 24:for(unsigned j=lane;j<2;j+=2) {
                uint64_t v=__double_as_longlong(__int2double_rn(*(int32_t*)(sp+addr+j*4)));
                e[fd+j]=div_rnd<-1,true>(e[fd+j],__longlong_as_double((v&randomx::dynamicMantissaMask)|masks[j]),mode);
            }break;
            case 25:for(unsigned j=lane;j<2;j+=2)e[fd+j]=sqrt_rnd<-1,true>(e[fd+j],mode);break;
            case 26:r[d]+=ins.imm;if(!(r[d]&ins.mask))pc=ins.target;break;
            case 27:mode=refRotate(src,(unsigned)ins.imm)&3;break;
            case 28:*(uint64_t*)(sp+((uint32_t)(r[d]+ins.imm)&ins.mask))=src;break;
            }
            __syncwarp(active_mask);
            pc=__shfl_sync(active_mask,pc,0,width);
            mode=__shfl_sync(active_mask,mode,0,width);
        }
        uint32_t read=ma;mx^=r[rr2]^r[rr3];mx&=CacheLineAlignMask;
        __syncwarp(active_mask);
        if(lane<8) {unsigned j=lane;r[j]^=*(const uint64_t*)(ds+read+j*8);*(uint64_t*)(sp+sp1+j*8)=r[j];}
        uint32_t temp=ma;ma=mx;mx=temp;
        if(lane<8)*(uint64_t*)(sp+sp0+lane*8)=__double_as_longlong(f[lane])^__double_as_longlong(e[lane]);
        __syncwarp(active_mask);
        sp0=sp1=0;
    }
    auto *out=(uint64_t*)((uint8_t*)states+index*VM_STATE_SIZE);
    if(lane<8){unsigned j=lane;out[j]=r[j];out[8+j]=__double_as_longlong(f[j])^__double_as_longlong(e[j]);out[16+j]=__double_as_longlong(e[j]);out[24+j]=__double_as_longlong(a[j]);}
    if(lane==0)((uint32_t*)rounding)[index]=mode;
}
