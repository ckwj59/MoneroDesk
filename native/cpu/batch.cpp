// XMR CPU batch adapter; uses the upstream RandomX pipelined hashing API.
#include <cstdint>
#include <cstring>
#include "../RandomX/src/randomx.h"
extern "C" __declspec(dllexport) int xmr_cpu_batch(randomx_vm *vm,const void *blob,size_t length,
    const uint32_t *nonces,size_t count,void *out,size_t output_size) {
    if(!vm||!blob||!nonces||!out||length<43||length>512||!count||count>256||output_size!=count*32)return 0;
    uint8_t candidate[512];std::memcpy(candidate,blob,length);
    auto set_nonce=[&](uint32_t nonce){for(unsigned j=0;j<4;++j)candidate[39+j]=uint8_t(nonce>>(j*8));};
    set_nonce(nonces[0]);randomx_calculate_hash_first(vm,candidate,length);
    for(size_t i=1;i<count;++i){set_nonce(nonces[i]);randomx_calculate_hash_next(vm,candidate,length,(uint8_t*)out+(i-1)*32);}
    randomx_calculate_hash_last(vm,(uint8_t*)out+(count-1)*32);
    return 1;
}
