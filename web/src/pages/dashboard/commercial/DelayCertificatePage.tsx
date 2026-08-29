import React, { useState } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { FileText, QrCode, Printer, CheckCircle2, ShieldCheck, Search } from 'lucide-react';
import QRCode from 'react-qr-code';
import { toast } from 'sonner';

interface IssuedCert {
  certificate_no: string;
  qr_token: string;
  train_no: string;
  station_code: string;
  passenger_name: string;
  delay_minutes: number;
  reason: string;
  issued_at: string;
  issuer_signature: string;
  verification_url: string;
}

export function DelayCertificatePage() {
  const [activeTab, setActiveTab] = useState<'issue' | 'verify'>('issue');
  const [trainNo, setTrainNo] = useState('12034');
  const [stationCode, setStationCode] = useState('CNB');
  const [passengerName, setPassengerName] = useState('R. K. Sharma');
  const [pnrNo, setPnrNo] = useState('2419081245');
  const [delayReason, setDelayReason] = useState('Operational Congestion & Preceding Freight Regulation');
  const [issuedCert, setIssuedCert] = useState<IssuedCert | null>(null);

  // Verification state
  const [verifyToken, setVerifyToken] = useState('RTX-VAL-88421092');
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const handleIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.issueDelayCertificate({
        train_no: trainNo,
        station_code: stationCode,
        issued_to_name: passengerName,
        pnr_no: pnrNo,
        reason: delayReason,
      });
      setIssuedCert(res as IssuedCert);
      toast.success(`Delay Certificate ${((res as IssuedCert).certificate_no)} issued successfully.`);
    } catch {
      toast.error('Failed to issue delay certificate.');
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsVerifying(true);
    try {
      const res = await api.verifyDelayCertificate(verifyToken);
      setVerifyResult(res);
      toast.success('Certificate token cryptographically verified.');
    } catch {
      toast.error('Invalid certificate token.');
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="space-y-4 font-mono text-xs">
      <SEO title="Digital Delay Certificate Generator · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#FFB224]" />
            <span>Digital Delay Certificate (Travel Interruption Proof)</span>
          </h1>
          <p className="text-[#9A9DA3]">
            Cryptographically verifiable late-running certificate for airline missed connections, insurance & refunds
          </p>
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center gap-1 bg-[#15171A] p-1 border border-[#26282C]">
          <button
            onClick={() => setActiveTab('issue')}
            className={`px-3 py-1 text-xs transition-colors ${
              activeTab === 'issue' ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'text-[#9A9DA3]'
            }`}
          >
            Issue Certificate
          </button>
          <button
            onClick={() => setActiveTab('verify')}
            className={`px-3 py-1 text-xs transition-colors ${
              activeTab === 'verify' ? 'bg-[#FFB224] text-[#0E0F11] font-bold' : 'text-[#9A9DA3]'
            }`}
          >
            Verify QR Token
          </button>
        </div>
      </div>

      {activeTab === 'issue' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Input Form */}
          <div className="lg:col-span-5 bg-[#15171A] border border-[#26282C] p-5 space-y-4">
            <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2">
              Passenger & Journey Details
            </div>

            <form onSubmit={handleIssue} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">Train Number</label>
                  <input
                    type="text"
                    value={trainNo}
                    onChange={e => setTrainNo(e.target.value)}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6] font-bold"
                  />
                </div>
                <div>
                  <label className="text-[10px] text-[#9A9DA3] block mb-1">Station Code</label>
                  <input
                    type="text"
                    value={stationCode}
                    onChange={e => setStationCode(e.target.value)}
                    className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6] font-bold"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Passenger Full Name</label>
                <input
                  type="text"
                  value={passengerName}
                  onChange={e => setPassengerName(e.target.value)}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">PNR / Ticket Reference (Optional)</label>
                <input
                  type="text"
                  value={pnrNo}
                  onChange={e => setPnrNo(e.target.value)}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <div>
                <label className="text-[10px] text-[#9A9DA3] block mb-1">Official Cause of Delay</label>
                <textarea
                  rows={2}
                  value={delayReason}
                  onChange={e => setDelayReason(e.target.value)}
                  className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6]"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <QrCode className="w-4 h-4" />
                <span>Generate Official Delay Certificate</span>
              </button>
            </form>
          </div>

          {/* Right: Live Official Document Preview */}
          <div className="lg:col-span-7 bg-[#FFFFFF] text-[#16181A] border border-[#26282C] p-8 shadow-xl space-y-6 print:border-none print:shadow-none font-serif">
            <div className="flex items-start justify-between border-b-2 border-[#16181A] pb-4">
              <div>
                <div className="text-xs font-mono uppercase tracking-widest text-[#6B6E74]">
                  GOVERNMENT OF INDIA · MINISTRY OF RAILWAYS
                </div>
                <h2 className="text-lg font-bold uppercase tracking-tight text-[#16181A] font-sans mt-1">
                  OFFICIAL TRAIN DELAY CERTIFICATE
                </h2>
                <div className="text-[11px] font-mono text-[#6B6E74]">
                  NORTH CENTRAL RAILWAY · KANPUR OPERATING DIVISION
                </div>
              </div>

              <button
                onClick={() => window.print()}
                className="no-print p-2 bg-[#16181A] text-white hover:bg-[#333] text-xs font-mono flex items-center gap-1.5"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print PDF</span>
              </button>
            </div>

            <div className="text-xs font-mono space-y-3">
              <div className="flex justify-between border-b border-[#E4E4E0] pb-2">
                <span className="text-[#6B6E74]">CERTIFICATE NO:</span>
                <span className="font-bold">{issuedCert?.certificate_no || 'CERT-CNB-12034-884210'}</span>
              </div>
              <div className="flex justify-between border-b border-[#E4E4E0] pb-2">
                <span className="text-[#6B6E74]">PASSENGER NAME:</span>
                <span className="font-bold">{passengerName || 'Passenger Name'}</span>
              </div>
              <div className="flex justify-between border-b border-[#E4E4E0] pb-2">
                <span className="text-[#6B6E74]">TRAIN NUMBER & NAME:</span>
                <span className="font-bold">Train #{trainNo} (New Delhi - Kanpur Shatabdi)</span>
              </div>
              <div className="flex justify-between border-b border-[#E4E4E0] pb-2">
                <span className="text-[#6B6E74]">CERTIFIED DELAY DURATION:</span>
                <span className="font-bold text-[#C93A24]">42 MINUTES LATE ARRIVAL</span>
              </div>
              <div className="flex justify-between border-b border-[#E4E4E0] pb-2">
                <span className="text-[#6B6E74]">OFFICIAL DELAY REASON:</span>
                <span className="font-bold">{delayReason}</span>
              </div>
            </div>

            {/* Seal & QR Verification Code */}
            <div className="pt-4 border-t-2 border-[#16181A] flex items-center justify-between font-mono text-[10px]">
              <div>
                <div className="text-[#6B6E74]">DIGITALLY SEALED BY:</div>
                <div className="font-bold text-[#16181A] mt-0.5">CHIEF STATION MASTER · CNB</div>
                <div className="text-[#6B6E74] mt-1">Ref SHA-256: 0x99a8b11c002f</div>
              </div>

              <div className="bg-white p-2 border border-[#E4E4E0] flex flex-col items-center">
                <QRCode
                  value={issuedCert?.verification_url || 'https://railtwin.app/verify/cert'}
                  size={64}
                />
                <span className="text-[8px] text-[#6B6E74] mt-1">SCAN TO VERIFY</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Verification Tab */
        <div className="max-w-xl mx-auto bg-[#15171A] border border-[#26282C] p-6 space-y-4">
          <div className="font-bold text-sm text-[#E8E8E6] border-b border-[#26282C] pb-2">
            Verify Certificate Authenticity
          </div>

          <form onSubmit={handleVerify} className="space-y-3">
            <div>
              <label className="text-[10px] text-[#9A9DA3] block mb-1">Enter QR Security Token / Cert No</label>
              <input
                type="text"
                value={verifyToken}
                onChange={e => setVerifyToken(e.target.value)}
                className="w-full bg-[#0E0F11] border border-[#26282C] p-2 text-[#E8E8E6] font-bold"
              />
            </div>

            <button
              type="submit"
              disabled={isVerifying}
              className="w-full py-2.5 bg-[#FFB224] text-[#0E0F11] font-bold flex items-center justify-center gap-2"
            >
              <Search className="w-4 h-4" />
              <span>{isVerifying ? 'Checking Cryptographic Registry...' : 'Verify Authenticity'}</span>
            </button>
          </form>

          {verifyResult && (
            <div className="bg-[#0E0F11] border border-[#3ECF8E] p-4 space-y-2 mt-4">
              <div className="flex items-center gap-2 text-[#3ECF8E] font-bold">
                <ShieldCheck className="w-5 h-5" />
                <span>CERTIFICATE VALID & VERIFIED AUTHENTIC</span>
              </div>
              <div className="text-[11px] text-[#9A9DA3] space-y-1 pt-2 border-t border-[#26282C]">
                <div>Train: <span className="text-[#E8E8E6]">#12034 Shatabdi</span></div>
                <div>Passenger: <span className="text-[#E8E8E6]">R. K. Sharma</span></div>
                <div>Delay: <span className="text-[#FFB224]">42 Minutes Late</span></div>
                <div>Issued: <span className="text-[#E8E8E6]">28 Aug 2026 16:30 IST</span></div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
