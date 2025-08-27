"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle, Lightbulb, ArrowRight, DollarSign, ShieldCheck, RefreshCw, SearchCheck } from 'lucide-react'

interface RecommendationModalProps {
  isOpen: boolean
  onClose: () => void
  onComplete: (recommendationType: string) => void // 선택된 추천 유형 전달
}

export default function RecommendationModal({ isOpen, onClose, onComplete }: RecommendationModalProps) {
  const [selectedRecommendationType, setSelectedRecommendationType] = useState<string | null>(null)

  const handleSelectType = (type: string) => {
    setSelectedRecommendationType(type)
    onComplete(type)
  }

  const handleClose = () => {
    setSelectedRecommendationType(null)
    onClose()
  }

  // const dummyAnalysisSummary = `
  //   <p><strong>${selectedCompanies.length > 0 ? selectedCompanies.join(", ") : "등록된 보험사 없음"}</strong> 보험 분석 결과:</p>
  //   <ul class="list-disc list-inside space-y-1 mt-2">
  //     <li>현재 보장 범위: ${selectedCompanies.includes("삼성생명") ? "생명보험, 건강보험" : "기본 실손보험"}</li>
  //     <li>주요 특약: ${selectedCompanies.includes("현대해상") ? "운전자 특약, 상해 특약" : "없음"}</li>
  //     <li>월 납입 보험료: 약 ${selectedCompanies.length * 50000}원</li>
  //     <li>강점: ${selectedCompanies.length > 1 ? "다양한 보험사 분산 가입으로 위험 분산" : "단일 보험사 집중으로 관리 용이"}</li>
  //     <li>개선 필요: ${selectedCompanies.includes("KB손해보험") ? "암 진단비 부족, 노후 실손 전환 고려" : "치아 보험, 해외 여행자 보험 부재"}</li>
  //   </ul>
  // `

  // const dummyRecommendation = `
  //   <p><strong>선택하신 "${selectedRecommendationType}"에 대한 맞춤 추천:</strong></p>
  //   <ul class="list-disc list-inside space-y-1 mt-2">
  //     <li><strong>보험료 절감 (예시):</strong> 현재 불필요한 특약 제거 및 갱신형 상품 비갱신형 전환으로 월 2만원 절감 가능.</li>
  //     <li><strong>보장 강화 (예시):</strong> 암 진단비 5천만원 추가 (월 3만원), 뇌혈관/심혈관 질환 특약 추가 (월 1.5만원)로 주요 질병 보장 강화.</li>
  //     <li><strong>회사 변경 (예시):</strong> 기존 A보험사에서 B보험사로 전환 시, 동일 보장 대비 월 1만원 저렴한 상품 추천.</li>
  //     <li><strong>맞춤 보장 (예시):</strong> 고객님의 라이프스타일에 맞춰 활동량 기반 할인 특약 및 건강 증진형 보험 상품 추천.</li>
  //   </ul>
  //   <p class="mt-4 text-sm text-gray-600">
  //     *위 내용은 가상의 분석 결과이며, 실제 상담을 통해 정확한 정보를 확인하세요.
  //   </p>
  // `

  const recommendationOptions = [
    {
      type: "보험금을 줄이고 싶어요",
      icon: DollarSign,
      description: "불필요한 지출을 줄이고 싶을 때",
      color: "bg-green-50 text-green-600 border-green-200"
    },
    {
      type: "더 나은 보장을 받고 싶어요",
      icon: ShieldCheck,
      description: "현재 보장이 부족하다고 느낄 때",
      color: "bg-blue-50 text-blue-600 border-blue-200"
    },
    {
      type: "보험 회사를 바꾸고 싶어요",
      icon: RefreshCw,
      description: "다른 보험사 상품을 알아보고 싶을 때",
      color: "bg-purple-50 text-purple-600 border-purple-200"
    },
    {
      type: "나에게 잘 맞는 보장의 회사를 찾고 싶어요",
      icon: SearchCheck,
      description: "개인 맞춤형 보험을 찾고 싶을 때",
      color: "bg-orange-50 text-orange-600 border-orange-200"
    },
  ]

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl">보험 추천</DialogTitle>
        </DialogHeader>
          <div className="space-y-6">
            <h3 className="text-lg font-semibold text-center">어떤 종류의 보험 추천을 원하시나요?</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendationOptions.map((option, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className={`h-auto p-4 text-left justify-start hover:shadow-md transition-all duration-200 ${option.color}`}
                  onClick={() => handleSelectType(option.type)}
                >
                  <div className="flex items-start space-x-3 w-full">
                    <div className="w-10 h-10 rounded-lg bg-white shadow-sm flex items-center justify-center">
                      <option.icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm mb-1">{option.type}</div>
                      <div className="text-xs text-gray-500 leading-relaxed">{option.description}</div>
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          </div>

        {/* {step === 1 && (
          <div className="space-y-6">
            <Card className="bg-blue-50 border-blue-200">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <CheckCircle className="h-5 w-5 mr-2 text-blue-600" />
                  현재 내 보험 분석 요약
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: dummyAnalysisSummary }} />
              </CardContent>
            </Card>

            <div className="flex justify-end">
              <Button
                onClick={handleNextStep}
                className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
              >
                다음 단계로 <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        )} */}

        {/* {step === 1 && (
          <div className="space-y-6">
            <Card className="bg-green-50 border-green-200">
              <CardHeader>
                <CardTitle className="flex items-center text-lg">
                  <Lightbulb className="h-5 w-5 mr-2 text-green-600" />
                  맞춤 보험 추천 및 분석
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: dummyRecommendation }} />
              </CardContent>
            </Card> */}

            {/* <div className="flex justify-end">
              <Button
                onClick={() => {
                  if (selectedRecommendationType) {
                    onComplete(selectedRecommendationType)
                  }
                  handleClose()
                }}
                className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
              >
                추천 완료
              </Button>
            </div>
          </div>
        )} */}
      </DialogContent>
    </Dialog>
  )
}
